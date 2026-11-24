using System;
using System.Linq;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

// Effects are added only to the generated scene; original models stay intact.
public static class HomateDeviceEffectsBuild
{
    static T Store<T>(T asset, string name) where T : UnityEngine.Object
    {
        string path = "Assets/HomateGenerated/" + name;
        var existing = AssetDatabase.LoadAssetAtPath<T>(path);
        if (existing == null) { AssetDatabase.CreateAsset(asset, path); return asset; }
        EditorUtility.CopySerialized(asset, existing);
        EditorUtility.SetDirty(existing);
        UnityEngine.Object.DestroyImmediate(asset);
        return existing;
    }

    static Material Material(string name, Color color)
    {
        var shader = Shader.Find("Universal Render Pipeline/Unlit");
        if (shader == null) throw new Exception("URP Unlit shader missing");
        var material = new Material(shader);
        material.SetColor("_BaseColor", color);
        material.SetFloat("_Cull", (float)CullMode.Off);
        return Store(material, name + ".mat");
    }

    static Renderer Indicator(Transform parent, Vector3 position, float diameter)
    {
        var dot = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        dot.name = "StatusIndicator";
        UnityEngine.Object.DestroyImmediate(dot.GetComponent<Collider>());
        dot.transform.position = position;
        dot.transform.localScale = Vector3.one * diameter;
        dot.transform.SetParent(parent, true);
        var renderer = dot.GetComponent<Renderer>();
        renderer.sharedMaterial = Material("DeviceIndicator", Color.black);
        renderer.shadowCastingMode = ShadowCastingMode.Off;
        return renderer;
    }

    public static void Configure(HomateDeviceSimulation.Binding binding, Vector3 homeCenter)
    {
        var renderers = binding.target.GetComponentsInChildren<Renderer>(true);
        if (renderers.Length == 0) throw new Exception("Missing model renderer: " + binding.id);
        var bounds = renderers[0].bounds;
        foreach (var r in renderers) bounds.Encapsulate(r.bounds);
        var direction = homeCenter - bounds.center;
        direction.y = 0;
        direction.Normalize();
        var effects = new GameObject("HomeMateEffect_" + binding.id).transform;
        binding.focusTarget = bounds.center;
        binding.focusPosition = bounds.center + direction * Mathf.Max(bounds.size.magnitude, 0.35f) + Vector3.up * bounds.size.y * 0.15f;

        if (binding.kind == "camera")
        {
            var lens = renderers.FirstOrDefault(r => r.name == "Lens") ?? renderers.Single(r => r.name == "glass");
            var body = renderers.FirstOrDefault(r => r.name == "Camera_Shape");
            direction = (lens.bounds.center - (body == null ? bounds.center : body.bounds.center)).normalized;
            binding.indicator = Indicator(effects, lens.bounds.center + direction * 0.014f + Vector3.up * 0.022f, 0.011f);
            binding.focusTarget = lens.bounds.center;
            binding.focusPosition = lens.bounds.center + direction * 0.38f + Vector3.up * 0.035f;
        }
        else if (binding.kind == "speaker")
        {
            binding.indicator = Indicator(effects, bounds.center + Vector3.up * (bounds.extents.y + 0.012f), 0.012f);
            binding.waves = new LineRenderer[3];
            var material = Material("SpeakerWave", new Color(0.05f, 0.8f, 1f));
            for (int i = 0; i < 3; i++)
            {
                var waveObject = new GameObject("SoundWave_" + i);
                waveObject.transform.SetParent(effects, false);
                waveObject.transform.position = bounds.center + Vector3.up * 0.055f;
                waveObject.transform.rotation = Quaternion.LookRotation(direction);
                var wave = waveObject.AddComponent<LineRenderer>();
                wave.useWorldSpace = false;
                wave.loop = true;
                wave.positionCount = 40;
                for (int p = 0; p < 40; p++) {
                    float angle = p * Mathf.PI * 2 / 40;
                    wave.SetPosition(p, new Vector3(Mathf.Cos(angle), Mathf.Sin(angle), 0));
                }
                wave.widthMultiplier = 0.005f;
                wave.sharedMaterial = material;
                wave.shadowCastingMode = ShadowCastingMode.Off;
                wave.enabled = false;
                binding.waves[i] = wave;
            }
            binding.focusPosition += Vector3.up * 0.1f;
        }
        else if (binding.kind == "fan")
        {
            var airflow = new GameObject("ExtractorAirflow");
            airflow.transform.SetParent(effects, false);
            airflow.transform.position = new Vector3(bounds.center.x, bounds.min.y - 0.4f, bounds.center.z);
            airflow.transform.rotation = Quaternion.Euler(-90, 0, 0);
            var particles = airflow.AddComponent<ParticleSystem>();
            var main = particles.main;
            main.playOnAwake = false;
            main.loop = true;
            main.startLifetime = 1.2f;
            main.startSpeed = 0.4f;
            main.startSize = 0.018f;
            main.maxParticles = 160;
            main.simulationSpace = ParticleSystemSimulationSpace.World;
            var shape = particles.shape;
            shape.shapeType = ParticleSystemShapeType.Box;
            shape.scale = new Vector3(bounds.size.x * 0.55f, bounds.size.z * 0.45f, 0.02f);
            var emission = particles.emission;
            emission.enabled = false;
            particles.GetComponent<ParticleSystemRenderer>().sharedMaterial = Material("ExtractorParticle", new Color(0.65f, 0.85f, 1f));
            particles.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            binding.airflow = particles;
            binding.indicator = Indicator(effects, new Vector3(bounds.center.x, bounds.min.y, bounds.center.z) + direction * bounds.extents.z, 0.022f);
            binding.focusTarget = new Vector3(bounds.center.x, bounds.min.y, bounds.center.z);
            binding.focusPosition = binding.focusTarget + direction * 1.2f - Vector3.up * 0.12f;
        }
        else if (binding.kind == "tv")
            ConfigureScreen(binding, bounds, homeCenter);
        else throw new Exception("Unsupported effect kind: " + binding.kind);
    }

    class Plane { public float area; public Bounds bounds; }
    static void ConfigureScreen(HomateDeviceSimulation.Binding binding, Bounds bounds, Vector3 homeCenter)
    {
        // TV is one atlas-textured mesh. Find its largest front-facing plane,
        // then overlay only that rectangle, preserving frame and stand.
        var mesh = binding.target.GetComponent<MeshFilter>().sharedMesh;
        var vertices = mesh.vertices;
        var triangles = mesh.triangles;
        var front = binding.target.transform.InverseTransformDirection(homeCenter - bounds.center).z >= 0 ? 1f : -1f;
        var planes = new Dictionary<int, Plane>();
        for (int i = 0; i < triangles.Length; i += 3)
        {
            var a = vertices[triangles[i]]; var b = vertices[triangles[i+1]]; var c = vertices[triangles[i+2]];
            var cross = Vector3.Cross(b-a, c-a);
            if (cross.sqrMagnitude < 1e-16f || cross.z * front / cross.magnitude < 0.95f) continue;
            int key = Mathf.RoundToInt((a.z + b.z + c.z) / 3f * 10000);
            if (!planes.TryGetValue(key, out var plane)) planes[key] = plane = new Plane { bounds = new Bounds(a, Vector3.zero) };
            plane.area += cross.magnitude * 0.5f;
            plane.bounds.Encapsulate(a); plane.bounds.Encapsulate(b); plane.bounds.Encapsulate(c);
        }
        var surface = planes.Values.OrderByDescending(p => p.area).FirstOrDefault();
        if (surface == null) throw new Exception("Cannot locate TV screen plane");
        var quad = GameObject.CreatePrimitive(PrimitiveType.Quad);
        quad.name = "HomeMateTVScreen";
        UnityEngine.Object.DestroyImmediate(quad.GetComponent<Collider>());
        quad.transform.SetParent(binding.target.transform, false);
        float offset = 0.002f / binding.target.transform.TransformVector(Vector3.forward).magnitude;
        quad.transform.localPosition = surface.bounds.center + Vector3.forward * front * offset;
        quad.transform.localRotation = Quaternion.identity;
        quad.transform.localScale = new Vector3(surface.bounds.size.x * 0.96f, surface.bounds.size.y * 0.96f, 1);
        var material = Material("TVScreen", Color.black);
        var texture = new Texture2D(256, 128, TextureFormat.RGB24, false);
        var bars = new[] { new Color(0.12f, 0.65f, 0.9f), new Color(0.1f, 0.8f, 0.65f), new Color(0.7f, 0.85f, 0.2f), new Color(0.9f, 0.4f, 0.2f) };
        for (int y = 0; y < 128; y++) for (int x = 0; x < 256; x++) texture.SetPixel(x, y, bars[x/64] * Mathf.Lerp(0.45f, 1f, y/127f));
        texture.Apply();
        material.SetTexture("_BaseMap", Store(texture, "TVPattern.asset"));
        EditorUtility.SetDirty(material);
        binding.screen = quad.GetComponent<Renderer>();
        binding.screen.sharedMaterial = material;
        binding.screen.shadowCastingMode = ShadowCastingMode.Off;
        binding.focusTarget = quad.transform.position;
        binding.focusPosition = quad.transform.position + binding.target.transform.forward * front * Mathf.Max(bounds.size.magnitude, 1f);
    }
}
