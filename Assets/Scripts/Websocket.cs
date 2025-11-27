using UnityEngine;
using NativeWebSocket;

public class Websocket : MonoBehaviour
{
    private WebSocket _ws;
    
    // Start is called once before the first execution of Update after the MonoBehaviour is created
    async void Start()
    {
        _ws = new WebSocket("ws://localhost:3000");
        
        _ws.OnOpen += async () =>
        {
            Debug.Log("Connection open");
            await _ws.SendText("Hello from Unity!");
            Debug.Log("Unity sent message to Python");
        };

        _ws.OnError += (e) =>
        {
            Debug.Log("Error! " + e);
        };

        _ws.OnClose += (e) =>
        {
            Debug.Log("Connection closed!");
        };

        _ws.OnMessage += (bytes) =>
        {
            Debug.Log("OnMessage!");
            string message = System.Text.Encoding.UTF8.GetString(bytes);
            Debug.Log("MSG: " + message);
        };

        await _ws.Connect();

    }

    // Update is called once per frame
    void Update()
    {
        #if !UNITY_WEBGL || UNITY_EDITOR
        _ws.DispatchMessageQueue();
        #endif
    }

    private async void OnApplicationQuit()
    {
        await _ws.Close();
    }
}
