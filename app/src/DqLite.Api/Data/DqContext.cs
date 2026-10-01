using Microsoft.EntityFrameworkCore;

namespace DqLite.Api.Data;

public class Dataset
{
    public int Id { get; set; }
    public required string Name { get; set; }
    public required string TableName { get; set; }
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
}

public class Rule
{
    public int Id { get; set; }
    public int DatasetId { get; set; }
    public required string Name { get; set; }
    // not_null | range | unique
    public required string Type { get; set; }
    public required string Column { get; set; }
    public decimal? Min { get; set; }
    public decimal? Max { get; set; }
    public bool Enabled { get; set; } = true;
}

public class RuleRun
{
    public int Id { get; set; }
    public int RuleId { get; set; }
    public DateTime StartedAt { get; set; }
    public int DurationMs { get; set; }
    // pass | fail | error
    public required string Status { get; set; }
    public int FailedRows { get; set; }
}

// Rows the rules check, so rule runs do real database work.
public class SampleRow
{
    public int Id { get; set; }
    public string? CustomerName { get; set; }
    public string? Email { get; set; }
    public decimal Amount { get; set; }
    public DateTime CreatedAt { get; set; }
}

public class DqContext(DbContextOptions<DqContext> options) : DbContext(options)
{
    public DbSet<Dataset> Datasets => Set<Dataset>();
    public DbSet<Rule> Rules => Set<Rule>();
    public DbSet<RuleRun> RuleRuns => Set<RuleRun>();
    public DbSet<SampleRow> SampleRows => Set<SampleRow>();

    protected override void OnModelCreating(ModelBuilder b)
    {
        b.Entity<Rule>().Property(r => r.Min).HasPrecision(18, 2);
        b.Entity<Rule>().Property(r => r.Max).HasPrecision(18, 2);
        b.Entity<SampleRow>().Property(r => r.Amount).HasPrecision(18, 2);
        b.Entity<RuleRun>().HasIndex(r => r.RuleId);
    }
}
