using UnityEngine;

namespace HomeMind
{
    /// <summary>
    /// Bind one Unity Light (or any GameObject enabled state) to an MQTT device id.
    /// Agent catalog example: room=living, type=light, id=light-living
    /// Topic: home/living/light/light-living/command
    /// </summary>
    public class MqttLightBinding : MonoBehaviour
    {
        [Header("MQTT identity (must match agent / MQTTX topic)")]
        [SerializeField] string room = "living";
        [SerializeField] string deviceType = "light";
        [SerializeField] string deviceId = "light-living";

        [Header("Scene target")]
        [Tooltip("If empty, uses Light on this GameObject or enables/disables this GameObject.")]
        [SerializeField] Light targetLight;
        [SerializeField] bool alsoToggleGameObject;

        [Header("Actions")]
        [SerializeField] string turnOnAction = "turn_on";
        [SerializeField] string turnOffAction = "turn_off";

        bool _on;

        void Awake()
        {
            if (targetLight == null)
                targetLight = GetComponent<Light>();
            if (targetLight != null)
                _on = targetLight.enabled;
            else
                _on = gameObject.activeSelf;
        }

        void OnEnable()
        {
            if (HomeMindMqttClient.Instance != null)
                HomeMindMqttClient.Instance.CommandReceived += OnCommand;
        }

        void Start()
        {
            // Instance may spawn in Awake of another object — re-subscribe safely
            if (HomeMindMqttClient.Instance != null)
            {
                HomeMindMqttClient.Instance.CommandReceived -= OnCommand;
                HomeMindMqttClient.Instance.CommandReceived += OnCommand;
            }
        }

        void OnDisable()
        {
            if (HomeMindMqttClient.Instance != null)
                HomeMindMqttClient.Instance.CommandReceived -= OnCommand;
        }

        void OnCommand(string topic, string payload)
        {
            if (!HomeMindMqttClient.TryParseCommandTopic(topic, out var r, out var t, out var id))
                return;
            if (r != room || t != deviceType || id != deviceId)
                return;
            if (!HomeMindMqttClient.TryGetAction(payload, out var action))
                return;

            if (action == turnOnAction)
                Apply(true);
            else if (action == turnOffAction)
                Apply(false);
            else
                Debug.LogWarning($"[MqttLightBinding] {deviceId} unknown action: {action}");
        }

        void Apply(bool on)
        {
            _on = on;
            if (targetLight != null)
                targetLight.enabled = on;
            if (alsoToggleGameObject || targetLight == null)
                gameObject.SetActive(on);

            Debug.Log($"[MqttLightBinding] {deviceId} → {(on ? "ON" : "OFF")}");

            if (HomeMindMqttClient.Instance != null)
                HomeMindMqttClient.Instance.PublishState(room, deviceType, deviceId, on);
        }

#if UNITY_EDITOR
        [ContextMenu("Debug: Turn On")]
        void DebugOn() => Apply(true);

        [ContextMenu("Debug: Turn Off")]
        void DebugOff() => Apply(false);
#endif
    }
}
