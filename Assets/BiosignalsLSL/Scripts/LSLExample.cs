using UnityEngine;

namespace BiossignalsLSL
{
    /// An example on how to use the LSL receiver and sender
    public class LSLExample : MonoBehaviour
    {
        public LSLGenericReceiver receiver;
        public LSLMarkerSender markers;

        [Header("Channel to receive from plux")]
        [SerializeField]
        public int channelIndex = 1;    
        [SerializeField]
        public float threshold = 0.5f; 
        private float lastValue = 0f;

        void OnEnable()
        {
            if (receiver != null)
            {
                receiver.OnChunkFloat += OnFloatChunk;
                receiver.OnChunkDouble += OnDoubleChunk;
                receiver.OnChunkInt16 += OnInt16Chunk;
            }
        }

        void OnDisable()
        {
            if (receiver != null)
            {
                receiver.OnChunkFloat -= OnFloatChunk;
                receiver.OnChunkDouble -= OnDoubleChunk;
                receiver.OnChunkInt16 -= OnInt16Chunk;
            }
        }

        void OnFloatChunk(float[,] data, double[] ts, int rows, int cols)
        {
            if (cols <= channelIndex || rows <= 0) return;
            float v = data[rows - 1, channelIndex];
            if (lastValue <= threshold && v > threshold) markers?.Send($"ch{channelIndex} v:{v:F3}");
            lastValue = v;
        }

        void OnDoubleChunk(double[,] data, double[] ts, int rows, int cols)
        {
            if (cols <= channelIndex || rows <= 0) return;
            float v = (float)data[rows - 1, channelIndex];
            if (lastValue <= threshold && v > threshold) markers?.Send($"ch{channelIndex} v:{v:F3}");
            lastValue = v;
        }

        void OnInt16Chunk(short[,] data, double[] ts, int rows, int cols)
        {
            if (cols <= channelIndex || rows <= 0) return;
            float v = data[rows - 1, channelIndex];
            if (lastValue <= threshold && v > threshold) markers?.Send($"ch{channelIndex} v:{v:F3}");
            lastValue = v;
        }
    }
}
