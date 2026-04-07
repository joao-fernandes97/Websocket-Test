using System.Collections.Generic;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

/// <summary>
/// Runtime settings panel.
///
/// Has a shared header with global settings(Host, Port, Apply-to-All button)
/// This script populates the settings cards below.
///
/// Per-fetcher cards are instantiated at runtime from a prefab, one per
/// HttpDataFetcher found in the scene.
///
/// Card prefab requirements
///  * A child TMP_Text named "Title" -- fetcher GameObject name.
///  * A child TMP_InputField named "Endpoint"
///  * A child TMP_InputField named "Interval"
///  * A child Toggle named "PollToggle"
///  * A child TMP_Text named "Status"
///  * A child Button named "ApplyButton"
///  * A child Button named "ResetButton"
/// </summary>
public class ConnectionSettingsUI : MonoBehaviour
{
    //Shared header — assign existing scene objects in the Inspector

    [Header("Shared Header (existing scene objects)")]
    [SerializeField] private TMP_InputField _hostField;
    [SerializeField] private TMP_InputField _portField;
    [SerializeField] private Button         _applyAllButton;
    [SerializeField] private TextMeshProUGUI _headerStatusLabel;

    //Per-fetcher cards

    [Header("Per-connection Cards")]
    [Tooltip("ScrollRect Content RectTransform — cards are parented here.")]
    [SerializeField] private RectTransform _scrollContent;
    [SerializeField] private GameObject    _cardPrefab;

    [Header("Optional")]
    [SerializeField] private TextMeshProUGUI _summaryLabel;

    //Private

    private HttpDataFetcher[] _fetchers = System.Array.Empty<HttpDataFetcher>();
    private readonly List<GameObject> _spawnedCards = new List<GameObject>();

    //Unity events

    private void OnEnable() => Refresh();

    public void Refresh()
    {
        //TODO: With the new EndpointManager we could use those references instead to populate this
        _fetchers = FindObjectsByType<HttpDataFetcher>(FindObjectsSortMode.InstanceID);

        PopulateHeader();
        BuildCards();

        if (_summaryLabel != null)
            _summaryLabel.text = $"{_fetchers.Length} connection{(_fetchers.Length == 1 ? "" : "s")} found";
    }

    #region Header
    private void PopulateHeader()
    {
        // Restore last saved values, falling back to the first fetcher's config.
        string defaultHost = _fetchers.Length > 0 ? _fetchers[0].Host : "127.0.0.1";
        int    defaultPort = _fetchers.Length > 0 ? _fetchers[0].Port : 8000;

        _hostField.text = PlayerPrefs.GetString("HttpFetcher.Shared.host", defaultHost);
        _portField.text = PlayerPrefs.GetInt   ("HttpFetcher.Shared.port", defaultPort).ToString();

        // Remove any previous listener before adding a fresh one (guard against
        // multiple Refresh() calls re-registering the same lambda).
        _applyAllButton.onClick.RemoveAllListeners();
        _applyAllButton.onClick.AddListener(OnApplyAll);
    }

    private void OnApplyAll()
    {
        if (!int.TryParse(_portField.text, out int port) || port < 1 || port > 65535)
        {
            SetHeaderStatus("Port must be 1–65535");
            return;
        }

        string host = _hostField.text.Trim();

        PlayerPrefs.SetString("HttpFetcher.Shared.host", host);
        PlayerPrefs.SetInt   ("HttpFetcher.Shared.port", port);
        PlayerPrefs.Save();

        foreach (HttpDataFetcher f in _fetchers)
        {
            f.Host = host;
            f.Port = port;
            f.ApplyAndRestart();
        }

        // Refresh the URL line on every card without rebuilding them.
        RefreshCardStatusLabels();
        SetHeaderStatus($"Applied to all — {host}:{port}");
    }

    private void SetHeaderStatus(string msg)
    {
        if (_headerStatusLabel != null)
            _headerStatusLabel.text = msg;
    }
    #endregion

    #region Cards
    private void BuildCards()
    {
        foreach (GameObject c in _spawnedCards) Destroy(c);
        _spawnedCards.Clear();

        foreach (HttpDataFetcher fetcher in _fetchers)
            _spawnedCards.Add(BuildCard(fetcher));
    }

    private GameObject BuildCard(HttpDataFetcher fetcher)
    {
        GameObject card = Instantiate(_cardPrefab, _scrollContent);

        // Named child lookups — names must match the prefab exactly.
        TMP_Text        title         = GetChild<TMP_Text>       (card, "Title");
        TMP_InputField  endpointField = GetChild<TMP_InputField> (card, "Endpoint");
        TMP_InputField  intervalField = GetChild<TMP_InputField> (card, "Interval");
        Toggle          pollToggle    = GetChild<Toggle>         (card, "PollToggle");
        TMP_Text        statusLabel   = GetChild<TMP_Text>       (card, "Status");
        Button          applyBtn      = GetChild<Button>         (card, "ApplyButton");
        Button          resetBtn      = GetChild<Button>         (card, "ResetButton");

        // Populate
        if (title != null)         title.text          = fetcher.gameObject.name;
        if (endpointField != null) endpointField.text  = fetcher.Endpoint;
        if (intervalField != null) intervalField.text  = fetcher.UpdateInterval.ToString("F1");
        if (pollToggle != null)    pollToggle.isOn      = fetcher.PollContinuously;
        if (statusLabel != null)   statusLabel.text     = $"URL: {fetcher.Url}";

        // Dim interval field when one-shot mode is active
        if (pollToggle != null && intervalField != null)
        {
            intervalField.interactable = pollToggle.isOn;
            pollToggle.onValueChanged.AddListener(on => intervalField.interactable = on);
        }

        // Apply
        if (applyBtn != null)
        {
            applyBtn.onClick.AddListener(() =>
            {
                if (intervalField != null &&
                    (!float.TryParse(intervalField.text,
                        System.Globalization.NumberStyles.Float,
                        System.Globalization.CultureInfo.InvariantCulture,
                        out float interval) || interval < 0.1f))
                {
                    if (statusLabel != null) statusLabel.text = "Interval must be ≥ 0.1 s";
                    return;
                }

                if (endpointField != null) fetcher.Endpoint         = endpointField.text.Trim();
                if (intervalField != null) fetcher.UpdateInterval   = float.Parse(intervalField.text,
                    System.Globalization.CultureInfo.InvariantCulture);
                if (pollToggle != null)    fetcher.PollContinuously = pollToggle.isOn;

                fetcher.ApplyAndRestart();
                if (statusLabel != null) statusLabel.text = $"{fetcher.Url}";
            });
        }

        // Reset
        if (resetBtn != null)
        {
            resetBtn.onClick.AddListener(() =>
            {
                fetcher.LoadSettings();
                if (endpointField != null) endpointField.text = fetcher.Endpoint;
                if (intervalField != null) intervalField.text = fetcher.UpdateInterval.ToString("F1");
                if (pollToggle != null)    pollToggle.isOn     = fetcher.PollContinuously;
                if (statusLabel != null)   statusLabel.text    = $"URL: {fetcher.Url}";
            });
        }

        return card;
    }

    private void RefreshCardStatusLabels()
    {
        for (int i = 0; i < _spawnedCards.Count && i < _fetchers.Length; i++)
        {
            TMP_Text lbl = GetChild<TMP_Text>(_spawnedCards[i], "Status");
            if (lbl != null) lbl.text = $"{_fetchers[i].Url}";
        }
    }
    #endregion

    //Helpers

    private static T GetChild<T>(GameObject parent, string childName) where T : Component
    {
        Transform t = parent.transform.Find(childName);
        if (t == null)
        {
            Debug.LogWarning($"[ConnectionSettingsUI] Child '{childName}' not found on '{parent.name}'.");
            return null;
        }
        return t.GetComponent<T>();
    }
}