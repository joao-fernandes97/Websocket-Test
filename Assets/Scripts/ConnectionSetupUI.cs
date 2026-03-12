using System.Collections.Generic;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

/// <summary>
/// Runtime settings panel that auto-discovers every HttpDataFetcher in the scene
/// and builds a scrollable config card for each one.
///
/// ── Scene setup ──────────────────────────────────────────────────────────────
///  1. Create a Canvas (Screen Space – Overlay, or World Space).
///  2. Add a child Panel as the panel root, attach this script to it.
///  3. Assign the four prefab references in the Inspector (see below).
///  4. Toggle the panel on/off however suits your app (key bind, button, etc.).
///     The panel calls Refresh() each time it is enabled to pick up any new fetchers.
///
/// ── Prefabs required ─────────────────────────────────────────────────────────
///  CardPrefab        – A VerticalLayoutGroup panel. Must contain child objects
///                      with the tags/names expected in BuildCard() below.
///  InputFieldPrefab  – TMP_InputField
///  TogglePrefab      – Unity Toggle
///  ButtonPrefab      – Button + TextMeshProUGUI child
///
/// All prefabs are standard Unity UI components – no custom scripts needed on them.
/// </summary>
public class ConnectionSetupUI : MonoBehaviour
{
    // ── Inspector refs ────────────────────────────────────────────────────────

    [Header("Layout")]
    [Tooltip("The ScrollRect's Content RectTransform where cards are spawned.")]
    [SerializeField] private RectTransform _scrollContent;

    [Header("Prefabs")]
    [SerializeField] private GameObject _cardPrefab;
    [SerializeField] private TMP_InputField _inputFieldPrefab;
    [SerializeField] private Toggle         _togglePrefab;
    [SerializeField] private Button         _buttonPrefab;

    [Header("Optional")]
    [Tooltip("A TMP label that shows how many fetchers were found.")]
    [SerializeField] private TextMeshProUGUI _summaryLabel;

    // ── Private ───────────────────────────────────────────────────────────────

    private readonly List<GameObject> _spawnedCards = new List<GameObject>();

    // ── Unity events ──────────────────────────────────────────────────────────

    private void OnEnable()  => Refresh();

    // ── Public API ────────────────────────────────────────────────────────────

    /// <summary>Destroy all cards and rebuild from the current scene state.</summary>
    public void Refresh()
    {
        ClearCards();

        // FindObjectsByType searches inactive objects too; change the flag if you
        // only want active ones.
        HttpDataFetcher[] fetchers =
            FindObjectsByType<HttpDataFetcher>(FindObjectsSortMode.InstanceID);

        foreach (HttpDataFetcher fetcher in fetchers)
            BuildCard(fetcher);

        if (_summaryLabel != null)
            _summaryLabel.text = $"{fetchers.Length} connection{(fetchers.Length == 1 ? "" : "s")} found";
    }

    // ── Private helpers ───────────────────────────────────────────────────────

    private void ClearCards()
    {
        foreach (GameObject card in _spawnedCards)
            Destroy(card);
        _spawnedCards.Clear();
    }

    private void BuildCard(HttpDataFetcher fetcher)
    {
        // ── Card root ─────────────────────────────────────────────────────────
        GameObject card = Instantiate(_cardPrefab, _scrollContent);
        _spawnedCards.Add(card);

        // Title label – looks for a child named "Title" with a TMP component.
        TextMeshProUGUI title = card.transform.Find("Title")?.GetComponent<TextMeshProUGUI>();
        if (title != null) title.text = fetcher.gameObject.name;

        // ── Input fields ──────────────────────────────────────────────────────
        TMP_InputField hostField     = SpawnInputField(card, "Host",            fetcher.Host);
        TMP_InputField portField     = SpawnInputField(card, "Port",            fetcher.Port.ToString(), TMP_InputField.ContentType.IntegerNumber);
        TMP_InputField endpointField = SpawnInputField(card, "Endpoint",        fetcher.Endpoint);
        TMP_InputField intervalField = SpawnInputField(card, "Interval (s)",    fetcher.UpdateInterval.ToString("F1"), TMP_InputField.ContentType.DecimalNumber);

        // ── Continuous poll toggle ────────────────────────────────────────────
        Toggle pollToggle = SpawnToggle(card, "Poll continuously", fetcher.PollContinuously);

        // Disable the interval field when one-shot mode is selected.
        pollToggle.onValueChanged.AddListener(on => intervalField.interactable = on);
        intervalField.interactable = fetcher.PollContinuously;

        // ── Status label ──────────────────────────────────────────────────────
        TextMeshProUGUI statusLabel = SpawnLabel(card, $"URL: {fetcher.Url}");

        // ── Apply button ──────────────────────────────────────────────────────
        Button applyBtn = SpawnButton(card, "Apply & Reconnect");
        applyBtn.onClick.AddListener(() =>
        {
            // Validate and apply
            if (!int.TryParse(portField.text, out int port) || port < 1 || port > 65535)
            {
                statusLabel.text = "⚠ Port must be 1–65535";
                return;
            }
            if (!float.TryParse(intervalField.text,
                    System.Globalization.NumberStyles.Float,
                    System.Globalization.CultureInfo.InvariantCulture,
                    out float interval) || interval < 0.1f)
            {
                statusLabel.text = "⚠ Interval must be ≥ 0.1 s";
                return;
            }

            fetcher.Host             = hostField.text.Trim();
            fetcher.Port             = port;
            fetcher.Endpoint         = endpointField.text.Trim();
            fetcher.UpdateInterval   = interval;
            fetcher.PollContinuously = pollToggle.isOn;

            fetcher.ApplyAndRestart();
            statusLabel.text = $"✓ Connected → {fetcher.Url}";
        });

        // ── Reset button ──────────────────────────────────────────────────────
        Button resetBtn = SpawnButton(card, "Reset to Saved");
        resetBtn.onClick.AddListener(() =>
        {
            fetcher.LoadSettings();
            hostField.text     = fetcher.Host;
            portField.text     = fetcher.Port.ToString();
            endpointField.text = fetcher.Endpoint;
            intervalField.text = fetcher.UpdateInterval.ToString("F1");
            pollToggle.isOn    = fetcher.PollContinuously;
            statusLabel.text   = $"URL: {fetcher.Url}";
        });
    }

    // ── Widget factory helpers ────────────────────────────────────────────────
    // Each spawns a labelled widget into the card's VerticalLayoutGroup.

    private TMP_InputField SpawnInputField(
        GameObject parent,
        string label,
        string value,
        TMP_InputField.ContentType contentType = TMP_InputField.ContentType.Standard)
    {
        // Label
        SpawnLabel(parent, label);

        TMP_InputField field = Instantiate(_inputFieldPrefab, parent.transform);
        field.text        = value;
        field.contentType = contentType;
        return field;
    }

    private Toggle SpawnToggle(GameObject parent, string label, bool value)
    {
        Toggle toggle = Instantiate(_togglePrefab, parent.transform);

        // Try to set the label text on the toggle's child.
        TextMeshProUGUI lbl = toggle.GetComponentInChildren<TextMeshProUGUI>();
        if (lbl != null) lbl.text = label;

        toggle.isOn = value;
        return toggle;
    }

    private Button SpawnButton(GameObject parent, string label)
    {
        Button btn = Instantiate(_buttonPrefab, parent.transform);
        TextMeshProUGUI lbl = btn.GetComponentInChildren<TextMeshProUGUI>();
        if (lbl != null) lbl.text = label;
        return btn;
    }

    private TextMeshProUGUI SpawnLabel(GameObject parent, string text)
    {
        GameObject go  = new GameObject($"Label_{text}", typeof(RectTransform));
        go.transform.SetParent(parent.transform, false);
        TextMeshProUGUI tmp = go.AddComponent<TextMeshProUGUI>();
        tmp.text     = text;
        tmp.fontSize = 14;
        return tmp;
    }
}
