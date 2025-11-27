using UnityEngine;
using LSL;
using System;

namespace BiossignalsLSL
{

    public class LSLGenericReceiver : MonoBehaviour
    {
        [Tooltip("The name that appears on Lab Recorder.0")]
        [SerializeField]
        public string streamKey = "";
        [Tooltip("Seconds to wait while opening the stream.")]
        [SerializeField]
        public double openTimeout = 10.0;
        [Tooltip("Max samples to read per Update call.")]
        [SerializeField]
        public int maxChunk = 512;
        [Tooltip("Enable to print the first few rows for debugging.")]
        [SerializeField]
        public bool logFirstRows = false;
        [Tooltip("How many rows to print when logging is enabled.")]
        [SerializeField]
        public int logRows = 5;

        // stream information
        public string ConnectedName { get; private set; } = "";
        public string ConnectedType { get; private set; } = "";
        public int ChannelCount { get; private set; } = 0;
        public double NominalSrate { get; private set; } = 0;
        public channel_format_t ChannelFormat { get; private set; } = channel_format_t.cf_undefined;

        // Event: (data2D, timestamps, rows, channels)
        public event Action<float[,], double[], int, int> OnChunkFloat;
        public event Action<double[,], double[], int, int> OnChunkDouble;
        public event Action<short[,], double[], int, int> OnChunkInt16;

        private StreamInlet inlet;
        private bool connected;

        void Start()
        {
            // Resolve
            StreamInfo chosen = LSL.LSL.resolve_stream("name", streamKey, 16, openTimeout / 2)[0];

            if (LSL.LSL.resolve_stream("name", streamKey, 16, openTimeout / 2).Length == 0)
            {
                Debug.LogError($"No LSL stream for '{streamKey}'.");
                return;
            }

            inlet = new StreamInlet(chosen, 360, (int)processing_options_t.proc_clocksync);
            inlet.open_stream(openTimeout);

            ChannelCount = inlet.info().channel_count();
            NominalSrate = inlet.info().nominal_srate();
            ChannelFormat = inlet.info().channel_format();

            ConnectedName = chosen.name();
            ConnectedType = chosen.type();

            Debug.Log($"Connected NAME='{ConnectedName}' TYPE='{ConnectedType}' CH={ChannelCount} SRATE={NominalSrate} FMT={ChannelFormat}");
            connected = true;
        }

        void Update()
        {
            if (!connected) return;
            if (ChannelCount <= 0) return;

            var ts = new double[Mathf.Max(1, maxChunk)];
            int n = 0;

            switch (ChannelFormat)
            {
                case channel_format_t.cf_double64:
                    {
                        var buf = new double[Mathf.Max(1, maxChunk), ChannelCount];
                        n = inlet.pull_chunk(buf, ts, 0.0);
                        if (n > 0)
                        {
                            if (logFirstRows) LogSome("double", buf, ts, n, ChannelCount);
                            OnChunkDouble?.Invoke(buf, ts, n, ChannelCount);
                        }
                        break;
                    }
                case channel_format_t.cf_int16:
                    {
                        var buf = new short[Mathf.Max(1, maxChunk), ChannelCount];
                        n = inlet.pull_chunk(buf, ts, 0.0);
                        if (n > 0)
                        {
                            if (logFirstRows) LogSome("int16", buf, ts, n, ChannelCount);
                            OnChunkInt16?.Invoke(buf, ts, n, ChannelCount);
                        }
                        break;
                    }
                default:
                    {
                        var buf = new float[Mathf.Max(1, maxChunk), ChannelCount];
                        n = inlet.pull_chunk(buf, ts, 0.0);
                        if (n > 0)
                        {
                            if (logFirstRows) LogSome("float", buf, ts, n, ChannelCount);
                            OnChunkFloat?.Invoke(buf, ts, n, ChannelCount);
                        }
                        break;
                    }
            }
        }

        void OnDisable() => inlet?.close_stream();

        //This is just to log information coming from the plux
        void LogSome<T>(string label, T[,] data, double[] ts, int rows, int cols)
        {
            int r = Mathf.Min(rows, Mathf.Max(1, logRows));
            System.Text.StringBuilder sb = new System.Text.StringBuilder();
            for (int i = 0; i < r; i++)
            {
                sb.Length = 0;
                sb.Append($"[{label}] t={ts[i]:F3} : [");
                for (int c = 0; c < cols; c++)
                {
                    sb.Append(data[i, c]);
                    if (c < cols - 1) sb.Append(", ");
                }
                sb.Append("]");
                Debug.Log(sb.ToString());
            }
            logFirstRows = false;
        }
    }
}
