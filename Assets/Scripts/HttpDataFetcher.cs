using System.Collections;
using UnityEngine;
using UnityEngine.Events;
using UnityEngine.Networking;

/// <summary>
/// Generic HTTP GET poller / one-shot fetcher.
/// Configure in the Inspector or at runtime via ConnectionSettingsUI.
/// Settings persist between sessions via PlayerPrefs, keyed by GameObject name.
/// </summary>
public class HttpDataFetcher : MonoBehaviour
{
    // ── Inspector configuration ───────────────────────────────────────────────

    [Header("Endpoint")]
    [SerializeField] private string _host     = "127.0.0.1";
    [SerializeField] private int    _port     = 8000;
    [SerializeField] private string _endpoint = "/bpm";

    [Header("Polling")]
    [Tooltip("Poll continuously at the interval, or fetch once and stop.")]
    [SerializeField] private bool  _pollContinuously = true;
    [SerializeField] private float _updateInterval   = 1.0f;

    [Header("Behaviour")]
    [SerializeField] private bool _fetchOnStart = true;

    // ── Events ────────────────────────────────────────────────────────────────

    [Header("Events")]
    public UnityEvent<string> OnSuccess = new UnityEvent<string>();
    public UnityEvent<string> OnFailure = new UnityEvent<string>();

    // ── Public state ──────────────────────────────────────────────────────────

    public string LatestJson { get; private set; } = string.Empty;
    public bool   IsFetching { get; private set; }
    public string Url        => $"http://{_host}:{_port}{_endpoint}";

    // ── Exposed config (for settings UI) ─────────────────────────────────────

    public string Host
    {
        get => _host;
        set => _host = value;
    }

    public int Port
    {
        get => _port;
        set => _port = value;
    }

    public string Endpoint
    {
        get => _endpoint;
        set => _endpoint = value.StartsWith("/") ? value : "/" + value;
    }

    public bool PollContinuously
    {
        get => _pollContinuously;
        set => _pollContinuously = value;
    }

    public float UpdateInterval
    {
        get => _updateInterval;
        set => _updateInterval = Mathf.Max(0.1f, value);
    }

    // ── PlayerPrefs persistence ───────────────────────────────────────────────

    // Keys are namespaced by GameObject name so multiple fetchers don't collide.
    private string PrefKey(string field) => $"HttpFetcher.{gameObject.name}.{field}";

    public void SaveSettings()
    {
        PlayerPrefs.SetString(PrefKey("host"),     _host);
        PlayerPrefs.SetInt   (PrefKey("port"),     _port);
        PlayerPrefs.SetString(PrefKey("endpoint"), _endpoint);
        PlayerPrefs.SetInt   (PrefKey("poll"),     _pollContinuously ? 1 : 0);
        PlayerPrefs.SetFloat (PrefKey("interval"), _updateInterval);
        PlayerPrefs.Save();
    }

    /// <summary>
    /// Loads persisted values, falling back to whatever was set in the Inspector
    /// if no saved value exists yet.
    /// </summary>
    public void LoadSettings()
    {
        _host             = PlayerPrefs.GetString(PrefKey("host"),     _host);
        _port             = PlayerPrefs.GetInt   (PrefKey("port"),     _port);
        _endpoint         = PlayerPrefs.GetString(PrefKey("endpoint"), _endpoint);
        _pollContinuously = PlayerPrefs.GetInt   (PrefKey("poll"),     _pollContinuously ? 1 : 0) == 1;
        _updateInterval   = PlayerPrefs.GetFloat (PrefKey("interval"), _updateInterval);
    }

    /// <summary>Save settings and immediately restart fetching with the new config.</summary>
    public void ApplyAndRestart()
    {
        SaveSettings();
        StopFetching();
        StartFetching();
    }

    // ── Lifecycle ─────────────────────────────────────────────────────────────

    private Coroutine _pollRoutine;

    private void Awake()     => LoadSettings();
    private void Start()     { if (_fetchOnStart) StartFetching(); }
    private void OnDisable() => StopFetching();

    // ── Public control ────────────────────────────────────────────────────────

    public void StartFetching()
    {
        StopFetching();
        _pollRoutine = StartCoroutine(
            _pollContinuously ? PollRoutine() : SingleFetchRoutine());
    }

    public void StopFetching()
    {
        if (_pollRoutine == null) return;
        StopCoroutine(_pollRoutine);
        _pollRoutine = null;
    }

    /// <summary>Trigger a single fetch right now, ignoring the polling schedule.</summary>
    public void Fetch() => StartCoroutine(SingleFetchRoutine());

    /// <summary>Override all three URL parts at once.</summary>
    public void Configure(string host, int port, string endpoint)
    {
        _host     = host;
        _port     = port;
        _endpoint = endpoint.StartsWith("/") ? endpoint : "/" + endpoint;
    }

    // ── Coroutines ────────────────────────────────────────────────────────────

    private IEnumerator PollRoutine()
    {
        while (true)
        {
            yield return FetchOnce();
            yield return new WaitForSeconds(_updateInterval);
        }
    }

    private IEnumerator SingleFetchRoutine() { yield return FetchOnce(); }

    private IEnumerator FetchOnce()
    {
        if (IsFetching) yield break;
        IsFetching = true;

        using (UnityWebRequest req = UnityWebRequest.Get(Url))
        {
            yield return req.SendWebRequest();

            if (req.result == UnityWebRequest.Result.Success)
            {
                LatestJson = req.downloadHandler.text;
                OnSuccess.Invoke(LatestJson);
            }
            else
            {
                string err = $"[HttpDataFetcher] {req.responseCode} – {req.error} ({Url})";
                Debug.LogWarning(err);
                OnFailure.Invoke(err);
            }
        }

        IsFetching = false;
    }
}