using System;
using System.Collections;
using UnityEngine;
using UnityEngine.Events;
using UnityEngine.Networking;

/// <summary>
/// Generic HTTP GET poller / one-shot fetcher.
/// Configure the endpoint in the Inspector, then listen to OnSuccess
/// with any component that needs the raw JSON string.
/// </summary>
public class HttpDataFetcher : MonoBehaviour
{
    // ── Inspector configuration ──────────────────────────────────────────────

    [Header("Endpoint")]
    [SerializeField] private string _host      = "127.0.0.1";
    [SerializeField] private int    _port      = 8000;
    [SerializeField] private string _endpoint  = "/bpm";   // leading slash required

    [Header("Polling")]
    [Tooltip("If true, fetches repeatedly at the given interval. If false, fetches once on Start.")]
    [SerializeField] private bool  _pollContinuously = true;
    [SerializeField] private float _updateInterval   = 1.0f;

    [Header("Behaviour")]
    [Tooltip("Fetch automatically when the component starts.")]
    [SerializeField] private bool _fetchOnStart = true;

    // ── Events ───────────────────────────────────────────────────────────────

    /// <summary>Fired with the raw JSON string on every successful response.</summary>
    [Header("Events")]
    public UnityEvent<string> OnSuccess = new UnityEvent<string>();

    /// <summary>Fired with the error message on failure.</summary>
    public UnityEvent<string> OnFailure = new UnityEvent<string>();

    // ── Public state ─────────────────────────────────────────────────────────

    /// <summary>The most recently received raw JSON string. Empty if no successful fetch yet.</summary>
    public string LatestJson { get; private set; } = string.Empty;

    /// <summary>True while a request is in flight.</summary>
    public bool IsFetching { get; private set; }

    // ── Runtime URL building ─────────────────────────────────────────────────

    public string Url => $"http://{_host}:{_port}{_endpoint}";

    /// <summary>Override host/port/endpoint at runtime before calling StartFetching().</summary>
    public void Configure(string host, int port, string endpoint)
    {
        _host     = host;
        _port     = port;
        _endpoint = endpoint.StartsWith("/") ? endpoint : "/" + endpoint;
    }

    // ── Lifecycle ────────────────────────────────────────────────────────────

    private Coroutine _pollRoutine;

    private void Start()
    {
        if (_fetchOnStart)
            StartFetching();
    }

    private void OnDisable() => StopFetching();

    // ── Public control ───────────────────────────────────────────────────────

    /// <summary>Begin polling (or fire a single request if polling is disabled).</summary>
    public void StartFetching()
    {
        StopFetching();
        _pollRoutine = StartCoroutine(_pollContinuously ? PollRoutine() : SingleFetchRoutine());
    }

    /// <summary>Stop any in-progress polling.</summary>
    public void StopFetching()
    {
        if (_pollRoutine != null)
        {
            StopCoroutine(_pollRoutine);
            _pollRoutine = null;
        }
    }

    /// <summary>Fire a single fetch right now, regardless of polling settings.</summary>
    public void Fetch() => StartCoroutine(SingleFetchRoutine());

    // ── Coroutines ───────────────────────────────────────────────────────────

    private IEnumerator PollRoutine()
    {
        while (true)
        {
            yield return FetchOnce();
            yield return new WaitForSeconds(Mathf.Max(0f, _updateInterval));
        }
    }

    private IEnumerator SingleFetchRoutine()
    {
        yield return FetchOnce();
    }

    private IEnumerator FetchOnce()
    {
        if (IsFetching) yield break;

        IsFetching = true;
        using (UnityWebRequest request = UnityWebRequest.Get(Url))
        {
            yield return request.SendWebRequest();

            if (request.result == UnityWebRequest.Result.Success)
            {
                LatestJson = request.downloadHandler.text;
                OnSuccess.Invoke(LatestJson);
            }
            else
            {
                string error = $"[HttpDataFetcher] {request.responseCode} – {request.error} ({Url})";
                Debug.LogWarning(error);
                OnFailure.Invoke(error);
            }
        }
        IsFetching = false;
    }
}
