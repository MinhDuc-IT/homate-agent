using UnityEngine;
using UnityEngine.InputSystem;

public class HomatePreviewCamera : MonoBehaviour
{
    [System.Serializable]
    public class RoomView
    {
        public string id;
        public Vector3 position;
        public Quaternion rotation;
        public float fieldOfView;
    }

    [SerializeField] RoomView[] rooms = new RoomView[0];
    [SerializeField] Vector3 target;
    [SerializeField] float distance = 20f;
    [SerializeField] float minimumDistance = 2f;
    [SerializeField] float maximumDistance = 100f;
    [SerializeField] float yaw = 135f;
    [SerializeField] float pitch = 45f;
    Vector3 overviewTarget;
    float overviewDistance;
    bool insideRoom;

    public void SetRooms(RoomView[] views) { rooms = views; }

    public void Frame(Bounds bounds)
    {
        target = bounds.center;
        var size = Mathf.Max(bounds.size.x, bounds.size.y, bounds.size.z, 1f);
        minimumDistance = size * 0.15f;
        maximumDistance = size * 4f;
        distance = size * 1.6f;
        overviewTarget = target;
        overviewDistance = distance;
        ApplyPose();
    }

    void Awake()
    {
        overviewTarget = target;
        overviewDistance = distance;
    }

    // Called by the same-origin WebGL bridge, with an ID from the build's view menu.
    [UnityEngine.Scripting.Preserve]
    public void SelectView(string id)
    {
        var camera = GetComponent<Camera>();
        if (id == "overview")
        {
            insideRoom = false;
            target = overviewTarget;
            distance = overviewDistance;
            yaw = 135f;
            pitch = 45f;
            camera.fieldOfView = 60f;
            camera.nearClipPlane = 0.3f;
            ApplyPose();
            return;
        }
        foreach (var room in rooms)
        {
            if (room.id != id) continue;
            insideRoom = true;
            transform.SetPositionAndRotation(room.position, room.rotation);
            yaw = transform.eulerAngles.y;
            pitch = Mathf.DeltaAngle(0f, transform.eulerAngles.x);
            camera.fieldOfView = room.fieldOfView;
            camera.nearClipPlane = 0.05f;
            return;
        }
    }

    void LateUpdate()
    {
        var mouse = Mouse.current;
        if (mouse == null) return;
        if (mouse.leftButton.isPressed)
        {
            var delta = mouse.delta.ReadValue();
            yaw += delta.x * 0.2f;
            pitch = Mathf.Clamp(pitch - delta.y * 0.2f, insideRoom ? -80f : 10f, 85f);
        }
        if (insideRoom)
        {
            if (mouse.leftButton.isPressed) transform.rotation = Quaternion.Euler(pitch, yaw, 0f);
            var camera = GetComponent<Camera>();
            camera.fieldOfView = Mathf.Clamp(camera.fieldOfView - mouse.scroll.ReadValue().y * 0.03f, 30f, 95f);
            return;
        }
        distance = Mathf.Clamp(distance * Mathf.Exp(-mouse.scroll.ReadValue().y * 0.001f), minimumDistance, maximumDistance);
        ApplyPose();
    }

    void ApplyPose()
    {
        transform.rotation = Quaternion.Euler(pitch, yaw, 0f);
        transform.position = target - transform.forward * distance;
    }
}
