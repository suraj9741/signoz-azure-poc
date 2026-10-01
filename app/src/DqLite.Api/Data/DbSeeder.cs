using Microsoft.EntityFrameworkCore;

namespace DqLite.Api.Data;

public static class DbSeeder
{
    // POC: EnsureCreated instead of migrations; SQL is private so the app creates its own schema.
    public static async Task SeedAsync(DqContext db, ILogger logger)
    {
        await db.Database.EnsureCreatedAsync();
        if (await db.Datasets.AnyAsync())
        {
            logger.LogInformation("Database already seeded");
            return;
        }

        logger.LogInformation("Seeding database");
        var dataset = new Dataset { Name = "Customer payments", TableName = "SampleRows" };
        db.Datasets.Add(dataset);
        await db.SaveChangesAsync();

        db.Rules.AddRange(
            new Rule { DatasetId = dataset.Id, Name = "Email not null", Type = "not_null", Column = "Email" },
            new Rule { DatasetId = dataset.Id, Name = "Customer name not null", Type = "not_null", Column = "CustomerName" },
            new Rule { DatasetId = dataset.Id, Name = "Amount in range", Type = "range", Column = "Amount", Min = 0, Max = 10000 },
            new Rule { DatasetId = dataset.Id, Name = "Email unique", Type = "unique", Column = "Email" });

        // ~5% bad rows so rules produce real failures.
        var rnd = new Random(42);
        for (var batch = 0; batch < 10; batch++)
        {
            for (var i = 0; i < 2000; i++)
            {
                var n = batch * 2000 + i;
                db.SampleRows.Add(new SampleRow
                {
                    CustomerName = rnd.NextDouble() < 0.03 ? null : $"Customer {n}",
                    Email = rnd.NextDouble() < 0.05 ? null : $"user{n % 19000}@example.com",
                    Amount = rnd.NextDouble() < 0.02 ? -rnd.Next(1, 500) : rnd.Next(1, 12000),
                    CreatedAt = DateTime.UtcNow.AddMinutes(-n)
                });
            }
            await db.SaveChangesAsync();
            db.ChangeTracker.Clear();
        }
        logger.LogInformation("Seeded {Rows} sample rows", 20000);
    }
}
