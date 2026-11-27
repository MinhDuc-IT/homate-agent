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
    Vector2 previousPointer;
    bool dragging;

    public void SetRooms(RoomView[] views) { rooms = views; }

    public void Frame(Bounds bounds)
    {
        target = bounds.center;
        var size = Mathf.Max(bounds.size.x, bounds.size.y, bounds.size.z, 1f);
        minimumDistance = 0.3f;
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
        var pointer = mouse.position.ReadValue();
        var delta = dragging ? pointer - previousPointer : Vector2.zero;
        previousPointer = pointer;
        dragging = mouse.leftButton.isPressed || mouse.rightButton.isPressed;
        if (!Application.isFocused || pointer.x < 0 || pointer.y < 0 || pointer.x > Screen.width || pointer.y > Screen.height) { dragging = false; return; }
        if (mouse.leftButton.wasPressedThisFrame || mouse.rightButton.wasPressedThisFrame) delta = Vector2.zero;
        if (mouse.leftButton.isPressed)
        {
            yaw += delta.x * 0.2f;
            pitch = Mathf.Clamp(pitch - delta.y * 0.2f, insideRoom ? -80f : 10f, 85f);
        }
        if (insideRoom)
        {
            if (mouse.leftButton.isPressed) transform.rotation = Quaternion.Euler(pitch, yaw, 0f);
            if (mouse.rightButton.isPressed)
                transform.position += (-transform.right * delta.x - transform.up * delta.y) * 0.005f;
            return;
        }
        if (mouse.rightButton.isPressed)
            target += (-transform.right * delta.x - transform.up * delta.y) * distance * 0.001f;
        ApplyPose();
    }

    [UnityEngine.Scripting.Preserve]
    public void Zoom(string direction) { ZoomAmount(direction == "in" ? 1f : -1f); }

    void ZoomAmount(float steps)
    {
        if (insideRoom) transform.position += transform.forward * (steps * 0.4f);
        else {
            distance = Mathf.Clamp(distance * Mathf.Pow(0.8f, steps), minimumDistance, maximumDistance);
            ApplyPose();
        }
    }

    public void Focus(Vector3 position, Vector3 lookAt)
    {
        insideRoom = true;
        transform.SetPositionAndRotation(position, Quaternion.LookRotation(lookAt - position));
        yaw = transform.eulerAngles.y;
        pitch = Mathf.DeltaAngle(0f, transform.eulerAngles.x);
        var camera = GetComponent<Camera>();
        camera.fieldOfView = 55f;
        camera.nearClipPlane = 0.01f;
    }

    void ApplyPose()
    {
        transform.rotation = Quaternion.Euler(pitch, yaw, 0f);
        transform.position = target - transform.forward * distance;
    }
}
