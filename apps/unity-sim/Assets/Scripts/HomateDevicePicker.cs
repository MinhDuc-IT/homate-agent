using System;
using System.Linq;
using System.Runtime.InteropServices;
using UnityEngine;
using UnityEngine.InputSystem;

// Selection only. Device writes remain in the web app and backend gateway.
public class HomateDevicePicker : MonoBehaviour
{
    public HomateDeviceSimulation simulation;
    Vector2 pressedAt;
    Vector2 previousPointer;
    float travel;
    HomateDeviceSimulation.Binding selected;
    LineRenderer outline;
#if UNITY_WEBGL && !UNITY_EDITOR
    [DllImport("__Internal")] static extern void HomateDeviceSelected(string id);
#endif

    void Awake()
    {
        var go = new GameObject("HomeMateSelection");
        outline = go.AddComponent<LineRenderer>();
        outline.sharedMaterial = new Material(Shader.Find("Universal Render Pipeline/Unlit"));
        outline.sharedMaterial.SetColor("_BaseColor", new Color(0.15f, 1f, 0.55f));
        outline.startWidth = outline.endWidth = 0.008f;
        outline.useWorldSpace = true;
        outline.enabled = false;
    }

    void Update()
    {
        var mouse = Mouse.current;
        if (mouse == null || Camera.main == null) return;
        var pointer = mouse.position.ReadValue();
        if (mouse.leftButton.wasPressedThisFrame) { pressedAt = pointer; travel = 0; }
        else if (mouse.leftButton.isPressed) travel += Vector2.Distance(previousPointer, pointer);
        previousPointer = pointer;
        if (mouse.leftButton.wasReleasedThisFrame && travel < 8f && Vector2.Distance(pressedAt, mouse.position.ReadValue()) < 8f)
        {
            var hits = Physics.RaycastAll(Camera.main.ScreenPointToRay(mouse.position.ReadValue()), 300f)
                .OrderBy(hit => hit.distance);
            string id = "";
            foreach (var hit in hits) {
                var binding = simulation.bindings.FirstOrDefault(b => hit.transform == b.target.transform || hit.transform.IsChildOf(b.target.transform));
                if (binding != null) { id = binding.id; break; }
                // Walls and furniture occlude devices behind them.
                if (!hit.collider.isTrigger) break;
            }
            SelectDevice(id);
#if UNITY_WEBGL && !UNITY_EDITOR
            HomateDeviceSelected(id);
#endif
        }
    }

    [UnityEngine.Scripting.Preserve]
    public void SelectDevice(string id)
    {
        selected = Array.Find(simulation.bindings, binding => binding.id == id);
        outline.enabled = selected != null;
    }

    void LateUpdate()
    {
        if (selected == null) return;
        var renderers = selected.target.GetComponentsInChildren<Renderer>().Where(r => r.enabled).ToArray();
        if (renderers.Length == 0) { outline.enabled = false; return; }
        var bounds = renderers[0].bounds;
        foreach (var renderer in renderers) bounds.Encapsulate(renderer.bounds);
        bounds.Expand(0.025f);
        var a = bounds.min; var b = bounds.max;
        var corners = new[] { new Vector3(a.x,a.y,a.z), new Vector3(b.x,a.y,a.z), new Vector3(b.x,a.y,b.z), new Vector3(a.x,a.y,b.z),
            new Vector3(a.x,b.y,a.z), new Vector3(b.x,b.y,a.z), new Vector3(b.x,b.y,b.z), new Vector3(a.x,b.y,b.z) };
        var route = new[] {0,1,2,3,0,4,5,1,5,6,2,6,7,3,7,4};
        outline.positionCount = route.Length;
        for (int i = 0; i < route.Length; i++) outline.SetPosition(i, corners[route[i]]);
    }
}
