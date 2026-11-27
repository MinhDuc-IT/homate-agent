using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;
using UnityEngine.SceneManagement;

public static class HomateDeviceBuild
{
    [Serializable] class Catalog { public SourceBinding[] bindings; public DeviceInfo[] devices; }
    [Serializable] class DeviceInfo { public string id; public string name; }
    [Serializable] class SourceBinding
    {
        public string device_id;
        public string object_name;
        public string source_ref;
        public string binding_kind;
    }

    public static HomateWebGLBuild.ViewOption[] Configure(Scene scene, string project)
    {
        var path = Path.GetFullPath(Path.Combine(project, "../backend/migrations/data/0006_casa_catalog.json"));
        var catalog = JsonUtility.FromJson<Catalog>(File.ReadAllText(path));
        var transforms = scene.GetRootGameObjects().SelectMany(root => root.GetComponentsInChildren<Transform>(true)).ToArray();
        var bindings = new List<HomateDeviceSimulation.Binding>();
        var focusOptions = new List<HomateWebGLBuild.ViewOption>();
        var lampPositions = catalog.bindings.Where(b => b.binding_kind == "light")
            .SelectMany(b => transforms.Single(t => t.name == b.object_name).GetComponentsInChildren<Light>(true))
            .Select(light => light.transform.position).ToArray();
        var center = lampPositions.Aggregate(Vector3.zero, (sum, position) => sum + position) / lampPositions.Length;
        foreach (var source in catalog.bindings)
        {
            var references = source.source_ref.Split(':');
            ulong sourceId = ulong.Parse(references[1]);
            var matches = transforms.Where(t => t.name == source.object_name &&
                (references[0] != "prefab_instance" || GlobalObjectId.GetGlobalObjectIdSlow(t.gameObject).targetPrefabId == sourceId)).ToArray();
            if (matches.Length != 1) throw new Exception("Ambiguous/missing simulation object: " + source.device_id);
            var target = matches[0].gameObject;
            var binding = new HomateDeviceSimulation.Binding { id = source.device_id, kind = source.binding_kind, target = target };
            if (source.binding_kind == "curtain")
            {
                string asset = source.object_name.StartsWith("estor") ? "Assets/estor.fbx" : "Assets/persiana.fbx";
                binding.opening = AssetDatabase.LoadAllAssetsAtPath(asset).OfType<AnimationClip>().Single(c => !c.name.StartsWith("__preview__"));
                foreach (var animator in target.GetComponentsInChildren<Animator>(true)) animator.enabled = false;
                Debug.Log("HomeMate curtain " + source.device_id + ": " + binding.opening.name + " curves=" + string.Join(";", AnimationUtility.GetCurveBindings(binding.opening).Select(c => c.path + ":" + c.propertyName)));
            }
            else if (source.binding_kind == "light" && target.GetComponentsInChildren<Light>(true).Length == 0)
                throw new Exception("No Light components: " + source.device_id);
            if (source.binding_kind != "light" && source.binding_kind != "curtain")
            {
                HomateDeviceEffectsBuild.Configure(binding, center);
            }
            else {
                var renderers = target.GetComponentsInChildren<Renderer>(true);
                var bounds = renderers.Length > 0 ? renderers[0].bounds : new Bounds(target.transform.position, Vector3.one * 0.2f);
                foreach (var renderer in renderers) bounds.Encapsulate(renderer.bounds);
                binding.focusTarget = bounds.center;
                var direction = (center - bounds.center).normalized;
                if (direction.sqrMagnitude < 0.1f) direction = Vector3.forward;
                binding.focusPosition = bounds.center + direction * Mathf.Max(bounds.size.magnitude * 1.2f, 0.7f);
            }
            foreach (var mesh in target.GetComponentsInChildren<MeshFilter>(true)) {
                if (mesh.sharedMesh == null || mesh.GetComponent<Collider>() != null) continue;
                mesh.gameObject.AddComponent<MeshCollider>().sharedMesh = mesh.sharedMesh;
            }
            focusOptions.Add(new HomateWebGLBuild.ViewOption {
                id = source.device_id, label = catalog.devices.Single(d => d.id == source.device_id).name
            });
            foreach (var light in target.GetComponentsInChildren<Light>(true)) light.lightmapBakeType = LightmapBakeType.Realtime;
            bindings.Add(binding);
        }
        if (bindings.Count != 27) throw new Exception("Expected 27 verified model bindings.");
        var controller = new GameObject("HomeMateDevices").AddComponent<HomateDeviceSimulation>();
        controller.bindings = bindings.ToArray();
        controller.gameObject.AddComponent<HomateDevicePicker>().simulation = controller;
        AssetDatabase.SaveAssets();
        return focusOptions.ToArray();
    }
}
