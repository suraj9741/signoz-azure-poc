# DQ Lite API — .NET 8 + OpenTelemetry .NET auto-instrumentation (no code change).
# Build context: signoz-poc/app

FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src
COPY src/DqLite.Api/DqLite.Api.csproj src/DqLite.Api/
RUN dotnet restore src/DqLite.Api/DqLite.Api.csproj
COPY src/ src/
RUN dotnet publish src/DqLite.Api/DqLite.Api.csproj -c Release -o /app --no-restore

FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS runtime

# ---- the "one image change": OpenTelemetry .NET auto-instrumentation layer ----
# Pinned release for repeatable builds (latest as of 30 Sept 2026). Override with --build-arg.
ARG OTEL_DOTNET_AUTO_VERSION=v1.17.0
ENV OTEL_DOTNET_AUTO_HOME=/otel-dotnet-auto
# The installer verifies assets with the GitHub CLI when available; the script and zip are
# fetched over HTTPS from the official release, so verification is skipped in this image.
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl unzip ca-certificates \
 && curl -sSfL "https://github.com/open-telemetry/opentelemetry-dotnet-instrumentation/releases/download/${OTEL_DOTNET_AUTO_VERSION}/otel-dotnet-auto-install.sh" -o /tmp/otel-install.sh \
 && SKIP_RELEASE_VERIFICATION=true sh /tmp/otel-install.sh \
 && rm /tmp/otel-install.sh \
 && apt-get purge -y curl unzip && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

# Same variables the upstream instrument.sh (v1.17) sets for linux-x64.
ENV CORECLR_ENABLE_PROFILING=1 \
    CORECLR_PROFILER={918728DD-259F-4A6A-AC2B-B85E1B658318} \
    CORECLR_PROFILER_PATH=/otel-dotnet-auto/linux-x64/OpenTelemetry.AutoInstrumentation.Native.so \
    DOTNET_STARTUP_HOOKS=/otel-dotnet-auto/net/OpenTelemetry.AutoInstrumentation.StartupHook.dll
# ---- end of instrumentation layer; exporter settings come from App Service app settings ----

WORKDIR /app
COPY --from=build /app .
ENV ASPNETCORE_HTTP_PORTS=8080
EXPOSE 8080
ENTRYPOINT ["dotnet", "DqLite.Api.dll"]
