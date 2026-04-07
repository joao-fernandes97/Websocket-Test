using System.Collections.Generic;
using UnityEngine;

public static class EndpointManager
{
    private static readonly Dictionary<string, HttpDataFetcher> _fetchers
        = new Dictionary<string, HttpDataFetcher>();
    private static readonly Dictionary<string, List<IConsumer>> _consumers
        = new Dictionary<string, List<IConsumer>>();

    /// <summary>
    /// Static dictionaries apparently can keep references across Play sessions
    /// This method and attribute ensures it's cleared whenever we hit Play
    /// Not sure if this is needed in the finished product but probably doesn't hurt
    /// </summary>
    [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
    private static void ResetOnLoad()
    {
        _fetchers.Clear();
        _consumers.Clear();
    }

    /// <summary>
    /// Registers a fetcher so consumers can 'subscribe' to it
    /// HttpDataFetcher must call this in Awake()
    /// </summary>
    /// <param name="fetcher"></param>
    public static void RegisterFetcher(HttpDataFetcher fetcher)
    {
        string name = fetcher.gameObject.name;

        if(_fetchers.ContainsKey(name))
        {
            Debug.LogWarning($"[EndpointManager] A fetcher named {name} is "+
            $"already registered and will be overwritten. Check for duplicate GameObject names.");
        }

        _fetchers[name] = fetcher;
        Debug.Log($"[EndpointManager] Fetcher registered: {name}");

        //Usually fetchers are registered first on Awake so this shouldn't happen
        //But in case there's Fetchers being dynamically generated or spawned
        //later this guards against that
        if(_consumers.TryGetValue(name, out List<IConsumer> pending) && pending.Count > 0)
        {
            Debug.Log($"[EndpointManager] Wiring {pending.Count} pre-registered " +
                      $"consumer(s) to late fetcher '{name}'");
            WireConsumersToFetcher(fetcher, pending);
        }
    }

    /// <summary>
    /// Removes a fetcher from the registry and notifies its consumers with an
    /// error so they can update their UI rather than silently going stale.
    /// HttpDataFetcher must call this in OnDestroy().
    /// </summary>
    public static void UnregisterFetcher(HttpDataFetcher fetcher)
    {
        string name = fetcher.gameObject.name;
 
        if (!_fetchers.Remove(name))
            return; // was never registered — nothing to do
 
        Debug.Log($"[EndpointManager] Fetcher unregistered: '{name}'");
 
        // Notify consumers that their source has gone away.
        if (_consumers.TryGetValue(name, out List<IConsumer> list))
        {
            foreach (IConsumer c in list)
            {
                try { c.OnFetchError($"[EndpointManager] Fetcher '{name}' was destroyed."); }
                catch (System.Exception e)
                {
                    Debug.LogError($"[EndpointManager] OnFetchError threw on consumer " +
                                   $"'{c.GetType().Name}': {e}");
                }
            }
        }
    }

    /// <summary>
    /// Registers a consumer and, if the target fetcher is already present,
    /// immediately wires the UnityEvent callbacks.
    /// IConsumer implementors must call this in Start().
    /// </summary>
    public static void RegisterConsumer(IConsumer consumer)
    {
        string name = consumer.FetcherName;
 
        if (!_consumers.ContainsKey(name))
            _consumers[name] = new List<IConsumer>();
 
        if (_consumers[name].Contains(consumer))
        {
            Debug.LogWarning($"[EndpointManager] Consumer '{consumer.GetType().Name}' " +
                             $"is already registered to '{name}'. Skipping duplicate.");
            return;
        }
 
        _consumers[name].Add(consumer);
        Debug.Log($"[EndpointManager] Consumer '{consumer.GetType().Name}' " +
                  $"registered to '{name}'.");
 
        // Wire immediately if the fetcher is already in the registry.
        if (_fetchers.TryGetValue(name, out HttpDataFetcher fetcher))
        {
            WireConsumersToFetcher(fetcher, new List<IConsumer> { consumer });
        }
        else
        {
            Debug.LogWarning($"[EndpointManager] Fetcher '{name}' not found yet. " +
                             $"Consumer '{consumer.GetType().Name}' will be wired when " +
                             $"the fetcher registers itself.");
        }
    }

    /// <summary>
    /// Removes a consumer and unwires its callbacks from the fetcher.
    /// IConsumer implementors must call this in OnDestroy().
    /// </summary>
    public static void UnregisterConsumer(IConsumer consumer)
    {
        string name = consumer.FetcherName;
 
        // Unwire from fetcher events.
        if (_fetchers.TryGetValue(name, out HttpDataFetcher fetcher))
            UnwireConsumerFromFetcher(fetcher, consumer);
 
        // Remove from the consumer list.
        if (_consumers.TryGetValue(name, out List<IConsumer> list))
        {
            list.Remove(consumer);
            if (list.Count == 0)
                _consumers.Remove(name);
        }
 
        Debug.Log($"[EndpointManager] Consumer '{consumer.GetType().Name}' " +
                  $"unregistered from '{name}'.");
    }

    private static void WireConsumersToFetcher(HttpDataFetcher fetcher,
                                                List<IConsumer> consumers)
    {
        foreach (IConsumer c in consumers)
        {
            fetcher.OnSuccess.AddListener(c.OnJsonReceived);
            fetcher.OnFailure.AddListener(c.OnFetchError);
        }
    }
 
    private static void UnwireConsumerFromFetcher(HttpDataFetcher fetcher,
                                                   IConsumer consumer)
    {
        fetcher.OnSuccess.RemoveListener(consumer.OnJsonReceived);
        fetcher.OnFailure.RemoveListener(consumer.OnFetchError);
    }
}
