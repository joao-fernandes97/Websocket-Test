using TMPro;
using UnityEngine;

/// <summary>
/// Displays live BPM value received from an HttpDataFetcher.
/// IMPORTANT
/// Any consumer classes must implement IConsumer
/// Must register itself into EndpointManager onStart()
/// Must unregister itself OnDestroy()
/// </summary>
public class BpmDisplay : MonoBehaviour, IConsumer
{
    [SerializeField] private TextMeshProUGUI _bpmText;

    [Tooltip("Must match GameObject name of target HttpDataFetcher exactly.")]
    [SerializeField] private string _fetcherName;

    #region Lifecycle
    private void Start() => EndpointManager.RegisterConsumer(this);
    private void OnDestroy() => EndpointManager.UnregisterConsumer(this);
    #endregion

    public string FetcherName => _fetcherName;

    public void OnJsonReceived(string json)
    {
        if (JsonFieldExtractor.TryGetFloat(json, "bpm", out float bpm))
        {
            _bpmText.text = $"BPM: {bpm:F1}";
        }
        else
        {
            _bpmText.text = "BPM: --";
            Debug.LogWarning($"[BpmDisplay] Could not parse 'bpm' field from: {json}");
        }
    }

    public void OnFetchError(string error)
    {
        _bpmText.text = "BPM: ERROR";
    }
}