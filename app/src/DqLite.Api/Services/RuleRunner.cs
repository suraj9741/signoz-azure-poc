using System.Diagnostics;
using System.Diagnostics.Metrics;
using DqLite.Api.Data;
using Microsoft.EntityFrameworkCore;

namespace DqLite.Api.Services;

// Custom spans and metrics use plain System.Diagnostics APIs (no OpenTelemetry package).
// Auto-instrumentation picks them up via OTEL_DOTNET_AUTO_*_ADDITIONAL_SOURCES=DqLite.Api.
public static class Telemetry
{
    public const string SourceName = "DqLite.Api";
    public static readonly ActivitySource Source = new(SourceName);
    public static readonly Meter Meter = new(SourceName);
    public static readonly Counter<long> RuleRuns = Meter.CreateCounter<long>("dq.rule_runs", description: "Rule executions");
    public static readonly Histogram<double> RuleRunDuration = Meter.CreateHistogram<double>("dq.rule_run.duration", unit: "ms");
    public static readonly Histogram<long> FailedRows = Meter.CreateHistogram<long>("dq.rule_run.failed_rows");
}

public class RuleRunner(DqContext db, ILogger<RuleRunner> logger)
{
    public async Task<RuleRun> RunAsync(Rule rule, CancellationToken ct)
    {
        using var activity = Telemetry.Source.StartActivity($"RuleRun {rule.Name}");
        activity?.SetTag("dq.rule.id", rule.Id);
        activity?.SetTag("dq.rule.type", rule.Type);
        activity?.SetTag("dq.dataset.id", rule.DatasetId);

        var sw = Stopwatch.StartNew();
        var run = new RuleRun { RuleId = rule.Id, StartedAt = DateTime.UtcNow, Status = "error" };
        try
        {
            run.FailedRows = await CountFailuresAsync(rule, ct);
            run.Status = run.FailedRows == 0 ? "pass" : "fail";
            logger.LogInformation("Rule {RuleId} {RuleName} finished: {Status}, {FailedRows} failed rows",
                rule.Id, rule.Name, run.Status, run.FailedRows);
        }
        catch (Exception ex)
        {
            activity?.SetStatus(ActivityStatusCode.Error, ex.Message);
            logger.LogError(ex, "Rule {RuleId} {RuleName} errored", rule.Id, rule.Name);
            throw;
        }
        finally
        {
            run.DurationMs = (int)sw.ElapsedMilliseconds;
            activity?.SetTag("dq.status", run.Status);
            activity?.SetTag("dq.failed_rows", run.FailedRows);
            var tags = new TagList { { "rule.type", rule.Type }, { "status", run.Status } };
            Telemetry.RuleRuns.Add(1, tags);
            Telemetry.RuleRunDuration.Record(run.DurationMs, new TagList { { "rule.type", rule.Type } });
            Telemetry.FailedRows.Record(run.FailedRows, new TagList { { "rule.type", rule.Type } });
            db.RuleRuns.Add(run);
            await db.SaveChangesAsync(CancellationToken.None);
        }
        return run;
    }

    private Task<int> CountFailuresAsync(Rule rule, CancellationToken ct)
    {
        var rows = db.SampleRows.AsNoTracking();
        var min = rule.Min ?? -999_999_999m;
        var max = rule.Max ?? 999_999_999m;
        return (rule.Type, rule.Column) switch
        {
            ("not_null", "Email") => rows.CountAsync(r => r.Email == null, ct),
            ("not_null", "CustomerName") => rows.CountAsync(r => r.CustomerName == null, ct),
            ("range", "Amount") => rows.CountAsync(r => r.Amount < min || r.Amount > max, ct),
            ("unique", "Email") => db.Database.SqlQuery<int>(
                    $"SELECT COALESCE(SUM(c), 0) AS [Value] FROM (SELECT COUNT(*) AS c FROM SampleRows WHERE Email IS NOT NULL GROUP BY Email HAVING COUNT(*) > 1) t")
                .SingleAsync(ct),
            _ => throw new NotSupportedException($"Rule type '{rule.Type}' on column '{rule.Column}' is not supported")
        };
    }
}
