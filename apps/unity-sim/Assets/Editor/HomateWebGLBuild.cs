using System;
using System.IO;
using System.Collections.Generic;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;

public static class HomateWebGLBuild
{
    [Serializable] public class ViewOption { public string id; public string label; }
    [Serializable] public class BuildStatus
    {
        public bool ready = true;
        public string scene = "HomePreview";
        public bool deviceSync = false;
        public ViewOption[] views;
    }
    [MenuItem("HomeMate/Build WebGL preview")]
    public static void Build()
    {
        var project = Directory.GetParent(Application.dataPath).FullName;
        var output = Path.GetFullPath(Path.Combine(project, "../web/public/unity"));
        var marker = Path.Combine(output, "build-status.json");
        Directory.CreateDirectory(output);
        if (File.Exists(marker)) File.Delete(marker);
        if (!EditorUserBuildSettings.SwitchActiveBuildTarget(BuildTargetGroup.WebGL, BuildTarget.WebGL))
            throw new Exception("Install WebGL Build Support in Unity Hub.");
        Directory.CreateDirectory(Path.Combine(project, "Assets/HomateGenerated"));
        AssetDatabase.Refresh();
        var scene = EditorSceneManager.OpenScene("Assets/Scenes/CASA.unity", OpenSceneMode.Single);
        int removed = 0;
        foreach (var root in scene.GetRootGameObjects())
            foreach (var transform in root.GetComponentsInChildren<Transform>(true))
            {
                removed += GameObjectUtility.RemoveMonoBehavioursWithMissingScript(transform.gameObject);
                // Remove legacy scripts from the generated preview so even Awake cannot start networking.
                foreach (var component in transform.GetComponents<MonoBehaviour>())
                    if (component != null && component.GetType().Assembly.GetName().Name == "Assembly-CSharp")
                        UnityEngine.Object.DestroyImmediate(component);
                foreach (var canvas in transform.GetComponents<Canvas>()) canvas.enabled = false;
                foreach (var audio in transform.GetComponents<AudioSource>())
                {
                    audio.playOnAwake = false;
                    audio.clip = null;
                    audio.enabled = false;
                }
            }
        // Replace missing legacy camera controllers with an isolated preview camera.
        var bounds = new Bounds(Vector3.zero, Vector3.one * 10f);
        bool found = false;
        var rooms = new List<HomatePreviewCamera.RoomView>();
        var menu = new List<ViewOption> { new ViewOption { id = "overview", label = "Toàn cảnh" } };
        var roomNames = new Dictionary<string, ViewOption> {
            { "Camera_SALON", new ViewOption { id = "living", label = "Phòng khách" } },
            { "Camera_HABITACION", new ViewOption { id = "bedroom", label = "Phòng ngủ" } },
            { "Camera_COCINA", new ViewOption { id = "kitchen", label = "Phòng bếp" } },
            { "Camera_ENTRADA", new ViewOption { id = "entrance", label = "Cửa vào" } }
        };
        foreach (var root in scene.GetRootGameObjects())
        {
            foreach (var camera in root.GetComponentsInChildren<Camera>(true))
            {
                if (roomNames.TryGetValue(camera.name, out var option))
                {
                    rooms.Add(new HomatePreviewCamera.RoomView {
                        id = option.id, position = camera.transform.position,
                        rotation = camera.transform.rotation, fieldOfView = camera.fieldOfView
                    });
                    menu.Add(option);
                    roomNames.Remove(camera.name);
                }
                camera.enabled = false;
            }
            foreach (var listener in root.GetComponentsInChildren<AudioListener>(true)) listener.enabled = false;
            foreach (var renderer in root.GetComponentsInChildren<MeshRenderer>())
            {
                if (!renderer.enabled) continue;
                if (!found) { bounds = renderer.bounds; found = true; }
                else bounds.Encapsulate(renderer.bounds);
            }
        }
        var view = new GameObject("HomeMatePreviewCamera");
        view.tag = "MainCamera";
        var previewCamera = view.AddComponent<Camera>();
        previewCamera.farClipPlane = Mathf.Max(bounds.size.magnitude * 10f, 1000f);
        var controller = view.AddComponent<HomatePreviewCamera>();
        controller.SetRooms(rooms.ToArray());
        controller.Frame(bounds);
        if (roomNames.Count > 0) throw new Exception("Missing room cameras: " + string.Join(", ", roomNames.Keys));
        const string preview = "Assets/HomateGenerated/HomePreview.unity";
        if (!EditorSceneManager.SaveScene(scene, preview, true)) throw new Exception("Cannot save preview scene.");
        PlayerSettings.WebGL.compressionFormat = WebGLCompressionFormat.Disabled;
        PlayerSettings.WebGL.template = "APPLICATION:Default";
        var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions {
            scenes = new[] { preview }, locationPathName = output,
            target = BuildTarget.WebGL, options = BuildOptions.None
        });
        if (report.summary.result != BuildResult.Succeeded) throw new Exception("WebGL build failed: " + report.summary.result);
        if (!File.Exists(Path.Combine(output, "index.html")) || Directory.GetFiles(Path.Combine(output, "Build"), "*.wasm").Length == 0)
            throw new Exception("Build output incomplete.");
        var index = Path.Combine(output, "index.html");
        var html = File.ReadAllText(index).Replace("</head>",
            "<style>html,body{margin:0;width:100%;height:100%;overflow:hidden}#unity-container{position:fixed!important;inset:0!important;transform:none!important;width:100%!important;height:100%!important}#unity-canvas{width:100%!important;height:100%!important}#unity-footer{display:none}</style></head>");
        html = html.Replace(".then((unityInstance) => {", ".then((unityInstance) => { window.homateUnityInstance = unityInstance; window.dispatchEvent(new Event('homate-unity-ready'));");
        html = html.Replace("</body>", "<script src=\"homate-bridge.js\"></script></body>");
        var status = JsonUtility.ToJson(new BuildStatus { views = menu.ToArray() });
        var bridge = File.ReadAllText(Path.Combine(project, "WebGL/bridge.js")).Replace("__HOMATE_BUILD_STATUS__", status);
        File.WriteAllText(Path.Combine(output, "homate-bridge.js"), bridge);
        File.WriteAllText(index, html);
        File.WriteAllText(marker, status);
        Debug.Log($"HomeMate WebGL ready at {output}; removed missing components: {removed}.");
    }
}
