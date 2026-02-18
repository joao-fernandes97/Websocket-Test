using TMPro;
using UnityEngine;

/// <summary>
/// Example consumer – drop this on the same (or any) GameObject alongside
/// HttpDataFetcher. Wire HttpDataFetcher.OnSuccess → this.OnJsonReceived
/// in the Inspector, or call fetcher.OnSuccess.AddListener(OnJsonReceived) in code.
///
/// This recreates the original BPM display and shows the pattern for other fields.
/// </summary>
[RequireComponent(typeof(HttpDataFetcher))]
public class BpmDisplay : MonoBehaviour
{
    [SerializeField] private TextMeshProUGUI _bpmText;

    // Called by HttpDataFetcher.OnSuccess (wire up in the Inspector)
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

    // Called by HttpDataFetcher.OnFailure (wire up in the Inspector)
    public void OnFetchError(string error)
    {
        _bpmText.text = "BPM: ERROR";
    }
}