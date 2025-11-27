using UnityEngine;
using LSL;

namespace BiossignalsLSL
{
    /// Simple LSL string marker outlet.
    public class LSLMarkerSender : MonoBehaviour
    {
        [Header("Marker Stream Information")]
        [SerializeField]
        public string streamName = "";
        [SerializeField]
        public string sourceId = "";

        private StreamOutlet outlet;

        void Awake()
        {
            var info = new StreamInfo(streamName, "Markers", 1, LSL.LSL.IRREGULAR_RATE, channel_format_t.cf_string, sourceId);
            outlet = new StreamOutlet(info);
            Debug.Log($"[LSLMarkerSender] Ready NAME='{streamName}'");
        }

        /// Send a single string marker.
        public void Send(string text)
        {
            if (outlet == null) return;
            outlet.push_sample(new string[] { text });
        }

    }
}
