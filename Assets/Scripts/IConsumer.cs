using UnityEngine;

/// <summary>
/// Interface for classes that want to receive data from and HttpDataFetcher
/// 
/// IMPORTANT
/// Fetcher name must match the GameObject name of the target Fetcher exactly (case-sensitive)
/// Implementors must call EndpointManager.RegisterConsumer(this) in Start()
/// Implementors must call EndpointManaget.UnregisterConsumer(this) in OnDestroy()
/// </summary>
public interface IConsumer
{
    string FetcherName {get;}
    void OnJsonReceived(string json);
    void OnFetchError(string error);
}
