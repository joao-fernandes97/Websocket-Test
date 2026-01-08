using System.Collections;
using TMPro;
using UnityEngine;
using UnityEngine.Networking;

public class BPMClient : MonoBehaviour
{
    [SerializeField] private TextMeshProUGUI _bpmText;
    [SerializeField] private float _updateInterval = 1.0f;
    
    private Coroutine _pollRoutine;
    // Start is called once before the first execution of Update after the MonoBehaviour is created
    void Start()
    {
        _pollRoutine = StartCoroutine(PollBPM());
    }

    void OnDisable()
    {
        if(_pollRoutine != null)
        {
            StopCoroutine(_pollRoutine);
            _pollRoutine = null;
        }
    }

    private IEnumerator PollBPM()
    {
        while(true)
        {
            using (UnityWebRequest request =
                   UnityWebRequest.Get("http://127.0.0.1:8000/bpm"))
            {
                yield return request.SendWebRequest();

                if(request.result == UnityWebRequest.Result.Success)
                {
                    BpmResponse response =
                        JsonUtility.FromJson<BpmResponse>(
                            request.downloadHandler.text    
                        );

                    _bpmText.text = $"BPM: {response.bpm}";
                }
                else
                {
                    _bpmText.text = "BPM:ERROR";
                    Debug.LogWarning(request.error);
                }
            }

            yield return new WaitForSeconds(_updateInterval);
        }
    }
}

[System.Serializable]
public class BpmResponse
{
    public float bpm;
}