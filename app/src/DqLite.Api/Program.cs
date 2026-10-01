using DqLite.Api.Data;
using DqLite.Api.Logging;
using DqLite.Api.Services;
using Microsoft.Data.SqlClient;
using Microsoft.EntityFrameworkCore;

var builder = WebApplication.CreateBuilder(args);

builder.Logging.AddProvider(new BlobTextLoggerProvider(builder.Configuration));

var connectionString = builder.Configuration.GetConnectionString("Default")
    ?? throw new InvalidOperationException("ConnectionStrings__Default is not set");
builder.Services.AddDbContext<DqContext>(o => o.UseSqlServer(connectionString, sql => sql.EnableRetryOnFailure(3)));
builder.Services.AddScoped<RuleRunner>();
builder.Services.AddProblemDetails();

var app = builder.Build();

app.UseExceptionHandler();
app.UseDefaultFiles();
app.UseStaticFiles();

using (var scope = app.Services.CreateScope())
{
    var db = scope.ServiceProvider.GetRequiredService<DqContext>();
    try
    {
        await DbSeeder.SeedAsync(db, app.Logger);
    }
    catch (Exception ex)
    {
        // Start anyway so /healthz and telemetry show the database problem.
        app.Logger.LogError(ex, "Database initialisation failed");
    }
}

// ---------------------------------------------------------------- health

app.MapGet("/healthz", async (DqContext db, CancellationToken ct) =>
    await db.Database.CanConnectAsync(ct)
        ? Results.Ok(new { status = "healthy", database = "ok" })
        : Results.Json(new { status = "unhealthy", database = "unreachable" }, statusCode: 503));

// ---------------------------------------------------------------- datasets

var datasets = app.MapGroup("/api/datasets");
datasets.MapGet("/", async (DqContext db) => await db.Datasets.AsNoTracking().ToListAsync());
datasets.MapGet("/{id:int}", async (int id, DqContext db) =>
    await db.Datasets.FindAsync(id) is { } d ? Results.Ok(d) : Results.NotFound());

// ---------------------------------------------------------------- rules (CRUD)

var rules = app.MapGroup("/api/rules");

rules.MapGet("/", async (DqContext db) => await db.Rules.AsNoTracking().ToListAsync());

rules.MapGet("/{id:int}", async (int id, DqContext db) =>
    await db.Rules.FindAsync(id) is { } r ? Results.Ok(r) : Results.NotFound());

rules.MapPost("/", async (RuleInput input, DqContext db, ILogger<Program> logger) =>
{
    if (Validate(input) is { } errors)
    {
        logger.LogWarning("Rejected rule create: {Errors}", string.Join("; ", errors.SelectMany(e => e.Value)));
        return Results.ValidationProblem(errors);
    }
    if (!await db.Datasets.AnyAsync(d => d.Id == input.DatasetId))
    {
        return Results.NotFound(new { error = $"Dataset {input.DatasetId} not found" });
    }
    var rule = new Rule { DatasetId = input.DatasetId, Name = input.Name!, Type = input.Type!, Column = input.Column!, Min = input.Min, Max = input.Max, Enabled = input.Enabled };
    db.Rules.Add(rule);
    await db.SaveChangesAsync();
    logger.LogInformation("Created rule {RuleId} {RuleName}", rule.Id, rule.Name);
    return Results.Created($"/api/rules/{rule.Id}", rule);
});

rules.MapPut("/{id:int}", async (int id, RuleInput input, DqContext db, ILogger<Program> logger) =>
{
    if (Validate(input) is { } errors)
    {
        return Results.ValidationProblem(errors);
    }
    if (await db.Rules.FindAsync(id) is not { } rule)
    {
        return Results.NotFound();
    }
    rule.Name = input.Name!;
    rule.Type = input.Type!;
    rule.Column = input.Column!;
    rule.Min = input.Min;
    rule.Max = input.Max;
    rule.Enabled = input.Enabled;
    await db.SaveChangesAsync();
    logger.LogInformation("Updated rule {RuleId}", id);
    return Results.Ok(rule);
});

rules.MapDelete("/{id:int}", async (int id, DqContext db, ILogger<Program> logger) =>
{
    if (await db.Rules.FindAsync(id) is not { } rule)
    {
        return Results.NotFound();
    }
    db.Rules.Remove(rule);
    await db.SaveChangesAsync();
    logger.LogInformation("Deleted rule {RuleId}", id);
    return Results.NoContent();
});

rules.MapPost("/{id:int}/run", async (int id, DqContext db, RuleRunner runner, CancellationToken ct) =>
    await db.Rules.FindAsync([id], ct) is { } rule
        ? Results.Ok(await runner.RunAsync(rule, ct))
        : Results.NotFound());

app.MapGet("/api/runs", async (int? ruleId, string? status, DqContext db) =>
{
    var q = db.RuleRuns.AsNoTracking().AsQueryable();
    if (ruleId is not null) q = q.Where(r => r.RuleId == ruleId);
    if (status is not null) q = q.Where(r => r.Status == status);
    return await q.OrderByDescending(r => r.Id).Take(100).ToListAsync();
});

// ---------------------------------------------------------------- fault injection (observability tests)

if (app.Configuration.GetValue("TEST_ENDPOINTS_ENABLED", false))
{
    var test = app.MapGroup("/api/test");

    test.MapGet("/status/{code:int}", (int code, ILogger<Program> logger) =>
    {
        logger.LogWarning("Test endpoint returning status {StatusCode}", code);
        return Results.StatusCode(code);
    });

    test.MapGet("/error", (ILogger<Program> logger) =>
    {
        logger.LogError("Test endpoint returning 500");
        return Results.Problem("Simulated server error", statusCode: 500);
    });

    test.MapGet("/slow", async (int? ms, ILogger<Program> logger) =>
    {
        var delay = Math.Clamp(ms ?? 3000, 0, 30000);
        logger.LogInformation("Test endpoint sleeping {DelayMs} ms", delay);
        await Task.Delay(delay);
        return Results.Ok(new { sleptMs = delay });
    });

    test.MapGet("/slow-sql", async (int? seconds, DqContext db, ILogger<Program> logger) =>
    {
        var s = Math.Clamp(seconds ?? 5, 1, 25);
        logger.LogInformation("Test endpoint running WAITFOR DELAY {Seconds}s", s);
        await db.Database.ExecuteSqlRawAsync($"WAITFOR DELAY '00:00:{s:00}'");
        return Results.Ok(new { sqlDelaySeconds = s });
    });

    test.MapGet("/exception", () =>
    {
        try
        {
            throw new TimeoutException("Simulated downstream timeout");
        }
        catch (Exception inner)
        {
            throw new InvalidOperationException("Simulated unhandled exception", inner);
        }
    });

    // Real SqlException 18456 (login failed) by connecting with a wrong password.
    test.MapGet("/db-fail", async (ILogger<Program> logger) =>
    {
        var bad = new SqlConnectionStringBuilder(connectionString) { Password = "wrong-password", ConnectTimeout = 5 };
        await using var conn = new SqlConnection(bad.ConnectionString);
        await conn.OpenAsync();
        return Results.Ok();
    });
}

app.Run();

static Dictionary<string, string[]>? Validate(RuleInput i)
{
    var errors = new Dictionary<string, string[]>();
    if (string.IsNullOrWhiteSpace(i.Name)) errors["name"] = ["Name is required"];
    if (i.Type is not ("not_null" or "range" or "unique")) errors["type"] = ["Type must be not_null, range or unique"];
    if (string.IsNullOrWhiteSpace(i.Column)) errors["column"] = ["Column is required"];
    if (i.Type == "range" && (i.Min is null || i.Max is null || i.Min > i.Max)) errors["range"] = ["Range rules need Min <= Max"];
    return errors.Count > 0 ? errors : null;
}

public record RuleInput(int DatasetId, string? Name, string? Type, string? Column, decimal? Min, decimal? Max, bool Enabled = true);
