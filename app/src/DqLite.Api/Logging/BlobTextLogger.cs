using System.Collections.Concurrent;
using System.Text;
using Azure.Identity;
using Azure.Storage.Blobs;

namespace DqLite.Api.Logging;

// Writes plain-text log files to Blob storage, the way many legacy apps do:
//   2026-09-30 10:15:02.123 [INF] DqLite.Api.Services.RuleRunner: message
// Each flush uploads a new block blob app-logs/yyyy/MM/dd/app-HHmmss-<instance>.log,
// which the collector's filelog receiver picks up through a blobfuse2 mount.
public sealed class BlobTextLoggerProvider : ILoggerProvider
{
    private readonly ConcurrentQueue<string> _queue = new();
    private readonly BlobContainerClient? _container;
    private readonly Timer? _timer;
    private readonly string _instance = ShortInstanceId();

    public BlobTextLoggerProvider(IConfiguration config)
    {
        var account = config["APP_LOGS_STORAGE_ACCOUNT"];
        var container = config["APP_LOGS_CONTAINER"] ?? "app-logs";
        if (string.IsNullOrEmpty(account))
        {
            return; // local run: blob logging off
        }
        _container = new BlobContainerClient(
            new Uri($"https://{account}.blob.core.windows.net/{container}"),
            new DefaultAzureCredential());
        _timer = new Timer(_ => Flush(), null, TimeSpan.FromSeconds(30), TimeSpan.FromSeconds(30));
    }

    private static string ShortInstanceId()
    {
        var id = Environment.GetEnvironmentVariable("WEBSITE_INSTANCE_ID") ?? Environment.MachineName;
        return id.Length > 8 ? id[..8] : id;
    }

    public ILogger CreateLogger(string categoryName) => new BlobTextLogger(categoryName, _queue, _container is not null);

    private void Flush()
    {
        if (_container is null || _queue.IsEmpty)
        {
            return;
        }
        var sb = new StringBuilder();
        while (_queue.TryDequeue(out var line))
        {
            sb.AppendLine(line);
        }
        var now = DateTime.UtcNow;
        var blobName = $"{now:yyyy/MM/dd}/app-{now:HHmmss}-{_instance}.log";
        try
        {
            _container.GetBlobClient(blobName).Upload(BinaryData.FromString(sb.ToString()), overwrite: true);
        }
        catch (Exception ex)
        {
            // Never let log shipping break the app; the OTLP log path still works.
            Console.Error.WriteLine($"Blob log upload failed: {ex.Message}");
        }
    }

    public void Dispose()
    {
        _timer?.Dispose();
        Flush();
    }

    private sealed class BlobTextLogger(string category, ConcurrentQueue<string> queue, bool enabled) : ILogger
    {
        public IDisposable? BeginScope<TState>(TState state) where TState : notnull => null;

        public bool IsEnabled(LogLevel logLevel) => enabled && logLevel >= LogLevel.Information;

        public void Log<TState>(LogLevel logLevel, EventId eventId, TState state, Exception? exception, Func<TState, Exception?, string> formatter)
        {
            if (!IsEnabled(logLevel))
            {
                return;
            }
            var level = logLevel switch
            {
                LogLevel.Information => "INF",
                LogLevel.Warning => "WRN",
                LogLevel.Error => "ERR",
                LogLevel.Critical => "CRT",
                _ => "DBG"
            };
            var message = formatter(state, exception).ReplaceLineEndings(" ");
            var line = $"{DateTime.UtcNow:yyyy-MM-dd HH:mm:ss.fff} [{level}] {category}: {message}";
            if (exception is not null)
            {
                line += $" | {exception.GetType().FullName}: {exception.Message.ReplaceLineEndings(" ")}";
            }
            queue.Enqueue(line);
        }
    }
}
