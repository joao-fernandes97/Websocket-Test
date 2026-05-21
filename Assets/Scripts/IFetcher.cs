using UnityEngine.Events;
 
/// <summary>
/// Interface for objects that fetch data and broadcast results to consumers.
///
/// IMPORTANT
/// FetcherName must match the GameObject name exactly (case-sensitive) —
/// EndpointManager uses it as the registry key.
/// Implementors must call EndpointManager.RegisterFetcher(this) in Awake()
/// and EndpointManager.UnregisterFetcher(this) in OnDestroy().
/// </summary>
public interface IFetcher
{
    /// <summary>GameObject name used as the registry key.</summary>
    string FetcherName { get; }
 
    void AddSuccessListener(UnityAction<string> callback);
    void RemoveSuccessListener(UnityAction<string> callback);
 
    void AddFailureListener(UnityAction<string> callback);
    void RemoveFailureListener(UnityAction<string> callback);
}

