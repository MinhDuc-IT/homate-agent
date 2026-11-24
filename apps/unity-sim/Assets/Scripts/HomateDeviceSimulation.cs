using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Scripting;

// Only displays acknowledged backend state; never sends device commands.
public class HomateDeviceSimulation : MonoBehaviour
{
    [Serializable] public class Binding
    {
        public string id;
        public string kind;
        public GameObject target;
        public AnimationClip opening;
        public Renderer indicator;
        public Renderer screen;
        public LineRenderer[] waves;
        public ParticleSystem airflow;
        public Vector3 focusPosition;
        public Vector3 focusTarget;
        [NonSerialized] public DeviceState state;
        [NonSerialized] public Light[] lights;
        [NonSerialized] public float[] intensities;
        [NonSerialized] public Renderer[] renderers;
        [NonSerialized] public MaterialPropertyBlock block;
    }
    [Serializable] public class DeviceState
    {
        public string id;
        public bool power;
        public float brightness = 100;
        public float position;
        public bool recording;
        public float volume;
        public float speed;
    }
    [Serializable] public class Snapshot { public DeviceState[] devices; }
    public Binding[] bindings;
    readonly Dictionary<string, Binding> lookup = new Dictionary<string, Binding>();

    void Awake()
    {
        foreach (var binding in bindings)
        {
            lookup.Add(binding.id, binding);
            binding.lights = binding.target.GetComponentsInChildren<Light>(true);
            binding.intensities = new float[binding.lights.Length];
            for (int i = 0; i < binding.lights.Length; i++)
            {
                binding.intensities[i] = Mathf.Max(binding.lights[i].intensity, 1f);
            }
            binding.renderers = binding.target.GetComponentsInChildren<Renderer>(true);
            binding.block = new MaterialPropertyBlock();
            foreach (var animator in binding.target.GetComponentsInChildren<Animator>(true)) animator.enabled = false;
        }
    }

    [Preserve] public void ApplySnapshot(string json)
    {
        if (string.IsNullOrEmpty(json) || json.Length > 65536) return;
        Snapshot snapshot;
        try { snapshot = JsonUtility.FromJson<Snapshot>(json); }
        catch (ArgumentException) { return; }
        if (snapshot?.devices == null) return;
        foreach (var state in snapshot.devices)
        {
            if (state == null || state.id == null || !lookup.TryGetValue(state.id, out var binding)) continue;
            binding.state = state;
            if (binding.kind == "light")
            {
                float level = state.power ? Mathf.Clamp01(state.brightness / 100f) : 0f;
                for (int i = 0; i < binding.lights.Length; i++)
                {
                    binding.lights[i].enabled = level > 0;
                    binding.lights[i].intensity = binding.intensities[i] * level;
                }
                foreach (var renderer in binding.renderers)
                {
                    var materials = renderer.sharedMaterials;
                    for (int slot = 0; slot < materials.Length; slot++)
                    {
                        var material = materials[slot];
                        if (material == null || !material.HasProperty("_EmissionColor") || !material.IsKeywordEnabled("_EMISSION")) continue;
                        renderer.GetPropertyBlock(binding.block, slot);
                        binding.block.SetColor("_EmissionColor", material.GetColor("_EmissionColor") * level);
                        renderer.SetPropertyBlock(binding.block, slot);
                    }
                }
            }
            else if (binding.kind == "curtain" && binding.opening != null)
            {
                binding.opening.SampleAnimation(binding.target, binding.opening.length * Mathf.Clamp01(state.position / 100f));
            }
            else if (binding.kind == "tv")
                Tint(binding.screen, state.power ? Color.white : Color.black, binding.block);
            else if (binding.kind == "fan" && binding.airflow != null)
            {
                float speed = Mathf.Clamp(state.speed, 0, 3);
                var emission = binding.airflow.emission;
                emission.enabled = speed > 0;
                emission.rateOverTime = speed * 16;
                var main = binding.airflow.main;
                main.startSpeed = 0.2f + speed * 0.16f;
                main.startLifetime = 0.45f / (0.2f + speed * 0.16f);
                if (speed > 0 && !binding.airflow.isPlaying) binding.airflow.Play();
                if (speed <= 0) binding.airflow.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
                Tint(binding.indicator, speed > 0 ? new Color(0.1f, 0.7f, 0.9f) : new Color(0.05f, 0.06f, 0.07f), binding.block);
            }
        }
        Update();
    }

    void Update()
    {
        foreach (var binding in bindings)
        {
            var state = binding.state;
            if (state == null) continue;
            if (binding.kind == "camera")
                Tint(binding.indicator, state.recording ? Color.red * (0.65f + Mathf.Sin(Time.time * 4f) * 0.25f) : new Color(0.04f, 0.04f, 0.04f), binding.block);
            if (binding.kind == "speaker")
            {
                float level = state.power ? Mathf.Clamp01(state.volume / 100f) : 0f;
                Tint(binding.indicator, state.power ? new Color(0.05f, 0.8f, 1f) : new Color(0.04f, 0.04f, 0.04f), binding.block);
                for (int i = 0; binding.waves != null && i < binding.waves.Length; i++)
                {
                    var wave = binding.waves[i];
                    wave.enabled = level > 0;
                    float phase = Mathf.Repeat(Time.time * 0.6f + i * 0.33f, 1f);
                    wave.transform.localScale = Vector3.one * (0.05f + phase * (0.06f + level * 0.1f));
                    wave.startColor = wave.endColor = new Color(0.05f, 0.5f + level * 0.5f, 0.7f + level * 0.3f);
                }
            }
        }
    }

    static void Tint(Renderer renderer, Color color, MaterialPropertyBlock block)
    {
        if (renderer == null) return;
        renderer.GetPropertyBlock(block);
        block.SetColor("_BaseColor", color);
        renderer.SetPropertyBlock(block);
    }

    [Preserve] public void FocusDevice(string id)
    {
        if (!lookup.TryGetValue(id, out var binding)) return;
        var camera = Camera.main;
        if (camera == null) return;
        var controller = camera.GetComponent<HomatePreviewCamera>();
        if (controller != null) controller.Focus(binding.focusPosition, binding.focusTarget);
    }
}
