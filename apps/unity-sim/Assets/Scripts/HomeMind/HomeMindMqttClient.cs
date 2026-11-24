using System;
using System.Collections.Concurrent;
using System.Text;
using UnityEngine;
using uPLibrary.Networking.M2Mqtt;
using uPLibrary.Networking.M2Mqtt.Messages;

namespace HomeMind
{
    /// <summary>
    /// MQTT bridge for the digital twin.
    /// Editor / standalone: TCP :1883 (works with M2Mqtt in this project).
    /// WebGL: TCP is unavailable — connect via WebSocket :9001 later.
    /// </summary>
    public class HomeMindMqttClient : MonoBehaviour
    {
        public static HomeMindMqttClient Instance { get; private set; }

        [Header("Broker (Editor / desktop)")]
        [SerializeField] string brokerHost = "127.0.0.1";
        [SerializeField] int brokerPort = 1883;
        [SerializeField] string clientIdPrefix = "unity-smarthome";

        [Header("Topics")]
        [SerializeField] string commandSubscribe = "home/+/+/+/command";

        [Header("Debug")]
        [SerializeField] bool logMessages = true;

        MqttClient _client;
        readonly ConcurrentQueue<Action> _mainThread = new ConcurrentQueue<Action>();

        public event Action<string, string> CommandReceived;

        void Awake()
        {
            if (Instance != null && Instance != this)
            {
                Destroy(gameObject);
                return;
            }
            Instance = this;
            DontDestroyOnLoad(gameObject);
        }

        void Start()
        {
#if UNITY_WEBGL && !UNITY_EDITOR
            Debug.LogError(
                "[HomeMind MQTT] WebGL cannot use TCP 1883. " +
                "Use Editor Play Mode for now, or add an MQTT-over-WebSocket client (ws://localhost:9001/mqtt).");
            return;
#else
            ConnectAndSubscribe();
#endif
        }

        void Update()
        {
            while (_mainThread.TryDequeue(out var action))
            {
                try { action?.Invoke(); }
                catch (Exception ex) { Debug.LogException(ex); }
            }
        }

        void OnDestroy()
        {
            Disconnect();
            if (Instance == this) Instance = null;
        }

        void OnApplicationQuit() => Disconnect();

#if !(UNITY_WEBGL && !UNITY_EDITOR)
        void ConnectAndSubscribe()
        {
            try
            {
                var clientId = $"{clientIdPrefix}-{Guid.NewGuid():N}".Substring(0, 23);
                _client = new MqttClient(brokerHost, brokerPort, false, null, null, MqttSslProtocols.None);
                _client.MqttMsgPublishReceived += OnPublishReceived;
                _client.Connect(clientId);
                _client.Subscribe(new[] { commandSubscribe }, new[] { MqttMsgBase.QOS_LEVEL_AT_MOST_ONCE });
                Debug.Log($"[HomeMind MQTT] Connected {brokerHost}:{brokerPort}, sub {commandSubscribe}");
            }
            catch (Exception ex)
            {
                Debug.LogError($"[HomeMind MQTT] Connect failed: {ex.Message}\nIs mqtt-broker running? (docker compose up -d mqtt-broker)");
            }
        }

        void OnPublishReceived(object sender, MqttMsgPublishEventArgs e)
        {
            var topic = e.Topic;
            var payload = Encoding.UTF8.GetString(e.Message);
            _mainThread.Enqueue(() =>
            {
                if (logMessages)
                    Debug.Log($"[HomeMind MQTT] ← {topic}\n{payload}");
                CommandReceived?.Invoke(topic, payload);
            });
        }
#endif

        void Disconnect()
        {
#if !(UNITY_WEBGL && !UNITY_EDITOR)
            try
            {
                if (_client != null && _client.IsConnected)
                {
                    _client.Disconnect();
                }
            }
            catch { /* ignore */ }
            _client = null;
#endif
        }

        /// <summary>Publish device state — topic home/{room}/{type}/{id}/state</summary>
        public void PublishState(string room, string deviceType, string deviceId, bool on, bool online = true)
        {
#if UNITY_WEBGL && !UNITY_EDITOR
            Debug.LogWarning("[HomeMind MQTT] PublishState skipped on WebGL (no WS client yet).");
            return;
#else
            if (_client == null || !_client.IsConnected) return;
            var topic = $"home/{room}/{deviceType}/{deviceId}/state";
            var json = $"{{\"state\":{{\"power\":{(on ? "true" : "false")}}},\"online\":{(online ? "true" : "false")}}}";
            _client.Publish(topic, Encoding.UTF8.GetBytes(json), MqttMsgBase.QOS_LEVEL_AT_MOST_ONCE, false);
            if (logMessages) Debug.Log($"[HomeMind MQTT] → {topic} {json}");
#endif
        }

        /// <summary>
        /// Parse home/{room}/{type}/{id}/command → parts; returns false if malformed.
        /// </summary>
        public static bool TryParseCommandTopic(string topic, out string room, out string deviceType, out string deviceId)
        {
            room = deviceType = deviceId = null;
            if (string.IsNullOrEmpty(topic)) return false;
            var parts = topic.Split('/');
            // home / room / type / id / command
            if (parts.Length != 5 || parts[0] != "home" || parts[4] != "command") return false;
            room = parts[1];
            deviceType = parts[2];
            deviceId = parts[3];
            return true;
        }

        public static bool TryGetAction(string json, out string action)
        {
            action = null;
            if (string.IsNullOrEmpty(json)) return false;
            // Minimal parse — avoids Newtonsoft dependency
            var key = "\"action\"";
            var i = json.IndexOf(key, StringComparison.Ordinal);
            if (i < 0) return false;
            var colon = json.IndexOf(':', i + key.Length);
            if (colon < 0) return false;
            var q1 = json.IndexOf('"', colon + 1);
            if (q1 < 0) return false;
            var q2 = json.IndexOf('"', q1 + 1);
            if (q2 < 0) return false;
            action = json.Substring(q1 + 1, q2 - q1 - 1);
            return !string.IsNullOrEmpty(action);
        }
    }
}
