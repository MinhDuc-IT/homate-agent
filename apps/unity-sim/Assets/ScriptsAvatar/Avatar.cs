using System.Collections;
using System.Collections.Generic;
using UnityEngine;


public class Avatar : MonoBehaviour
{
    public Camera previewCamera; // OPTIONAL
    public Animator animator;
    public LayerMask ground;
    public bool footTracking = true;
    public float footGroundOffset = .1f;
    [Header("Calibration")]
    public bool useCalibrationData = false;
    public PersistentCalibrationData calibrationData;

    public bool Calibrated { get; private set; }

    private PipeServer server;
    private InitialCalibration initialCalibration;

    private Quaternion initialRotation;
    private Vector3 initialPosition;
    private Quaternion targetRot;

    private Dictionary<HumanBodyBones, List<CalibrationData>> parentCalibrationData = new Dictionary<HumanBodyBones, List<CalibrationData>>();
    private CalibrationData spineUpDown, hipsTwist, chest, head;

    private void Start()
    {
        initialRotation = transform.rotation;
        initialPosition = transform.position;

        if (calibrationData && useCalibrationData)
        {
            CalibrateFromPersistent();
        }

        server = FindObjectOfType<PipeServer>();
        initialCalibration = FindObjectOfType<InitialCalibration>();
        if (server == null)
        {
            Debug.LogError("You must have a PipeServer in the scene!");
        }
    }

    public void CalibrateFromPersistent()
    {
        parentCalibrationData.Clear();

        if (calibrationData)
        {
            foreach (PersistentCalibrationData.CalibrationEntry d in calibrationData.parentCalibrationData)
            {
                List<CalibrationData> calibrationDatas = new List<CalibrationData>();
                parentCalibrationData.Add(d.bone, calibrationDatas);
                foreach (var calibration in d.data)
                {
                    calibrationDatas.Add(calibration.ReconstructReferences());

                }

            }
            spineUpDown = calibrationData.spineUpDown.ReconstructReferences();
            hipsTwist = calibrationData.hipsTwist.ReconstructReferences();
            chest = calibrationData.chest.ReconstructReferences();
            head = calibrationData.head.ReconstructReferences();
        }

        animator.enabled = false; // disable animator to stop interference.
        Calibrated = true;
    }
    public void Calibrate()
    {
        // Here we store the values of variables required to do the correct rotations at runtime.
        print("Calibrating on " + gameObject.name);

        parentCalibrationData.Clear();

        // Manually setting calibration data for the spine chain as we want really specific control over that.
        spineUpDown = new CalibrationData(animator.transform, animator.GetBoneTransform(HumanBodyBones.Spine), animator.GetBoneTransform(HumanBodyBones.Neck),
            server.GetVirtualHip(), server.GetVirtualNeck());
        hipsTwist = new CalibrationData(animator.transform, animator.GetBoneTransform(HumanBodyBones.Hips), animator.GetBoneTransform(HumanBodyBones.Hips),
            server.GetLandmark(Landmark.RIGHT_HIP), server.GetLandmark(Landmark.LEFT_HIP));
        chest = new CalibrationData(animator.transform, animator.GetBoneTransform(HumanBodyBones.Chest), animator.GetBoneTransform(HumanBodyBones.Chest),
            server.GetLandmark(Landmark.RIGHT_HIP), server.GetLandmark(Landmark.LEFT_HIP));
        head = new CalibrationData(animator.transform, animator.GetBoneTransform(HumanBodyBones.Neck), animator.GetBoneTransform(HumanBodyBones.Head),
            server.GetVirtualNeck(), server.GetLandmark(Landmark.NOSE));

        // Adding calibration data automatically for the rest of the bones.
        AddCalibration(HumanBodyBones.RightUpperArm, HumanBodyBones.RightLowerArm,
            server.GetLandmark(Landmark.RIGHT_SHOULDER), server.GetLandmark(Landmark.RIGHT_ELBOW));
        AddCalibration(HumanBodyBones.RightLowerArm, HumanBodyBones.RightHand,
            server.GetLandmark(Landmark.RIGHT_ELBOW), server.GetLandmark(Landmark.RIGHT_WRIST));

        AddCalibration(HumanBodyBones.RightUpperLeg, HumanBodyBones.RightLowerLeg,
            server.GetLandmark(Landmark.RIGHT_HIP), server.GetLandmark(Landmark.RIGHT_KNEE));
        AddCalibration(HumanBodyBones.RightLowerLeg, HumanBodyBones.RightFoot,
            server.GetLandmark(Landmark.RIGHT_KNEE), server.GetLandmark(Landmark.RIGHT_ANKLE));

        AddCalibration(HumanBodyBones.LeftUpperArm, HumanBodyBones.LeftLowerArm,
            server.GetLandmark(Landmark.LEFT_SHOULDER), server.GetLandmark(Landmark.LEFT_ELBOW));
        AddCalibration(HumanBodyBones.LeftLowerArm, HumanBodyBones.LeftHand,
            server.GetLandmark(Landmark.LEFT_ELBOW), server.GetLandmark(Landmark.LEFT_WRIST));

        AddCalibration(HumanBodyBones.LeftUpperLeg, HumanBodyBones.LeftLowerLeg,
            server.GetLandmark(Landmark.LEFT_HIP), server.GetLandmark(Landmark.LEFT_KNEE));
        AddCalibration(HumanBodyBones.LeftLowerLeg, HumanBodyBones.LeftFoot,
            server.GetLandmark(Landmark.LEFT_KNEE), server.GetLandmark(Landmark.LEFT_ANKLE));

        if (footTracking)
        {
            AddCalibration(HumanBodyBones.LeftFoot, HumanBodyBones.LeftToes,
                server.GetLandmark(Landmark.LEFT_ANKLE), server.GetLandmark(Landmark.LEFT_FOOT_INDEX));
            AddCalibration(HumanBodyBones.RightFoot, HumanBodyBones.RightToes,
                server.GetLandmark(Landmark.RIGHT_ANKLE), server.GetLandmark(Landmark.RIGHT_FOOT_INDEX));
        }

        animator.enabled = false; // disable animator to stop interference.
        Calibrated = true;

    }

    public void StoreCalibration()
    {
        if (!calibrationData)
        {
            Debug.LogError("Optional calibration data must be assigned to store into.");
            return;
        }

        List<PersistentCalibrationData.CalibrationEntry> calibrations = new List<PersistentCalibrationData.CalibrationEntry>();
        foreach (KeyValuePair<HumanBodyBones, List<CalibrationData>> k in parentCalibrationData)
        {
            calibrations.Add(new PersistentCalibrationData.CalibrationEntry() { bone = k.Key, data = k.Value });
        }
        calibrationData.parentCalibrationData = calibrations.ToArray();

        calibrationData.spineUpDown = spineUpDown;
        calibrationData.hipsTwist = hipsTwist;
        calibrationData.chest = chest;
        calibrationData.head = head;

        calibrationData.Dirty();

        print("Completed storing calibration data " + calibrationData.name);
    }
    private void AddCalibration(HumanBodyBones parent, HumanBodyBones child, Transform trackParent, Transform trackChild)
    {
        List<CalibrationData> list;

        // animator.GetBoneTransform(parent).rotation = trackParent.rotation;
        // animator.GetBoneTransform(child).rotation = trackChild.rotation;
        // animator.GetBoneTransform(parent).position = trackParent.position;
        // animator.GetBoneTransform(child).position = trackChild.position;
        if (!parentCalibrationData.TryGetValue(parent, out list))
        {
            list = new List<CalibrationData>();
            parentCalibrationData.Add(parent, list);
        }
        list.Add(new CalibrationData(animator.transform, animator.GetBoneTransform(parent), animator.GetBoneTransform(child),
            trackParent, trackChild));
    }

    private bool isActive = false;

    private IEnumerator ToggleBooleanAfterSeconds(float seconds)
    {
        while (true)
        {
            // Wait for the specified amount of time
            yield return new WaitForSeconds(seconds);

            // Toggle the boolean value
            isActive = false;

            // Optional: Log for debugging
            Debug.Log($"Boolean toggled: {isActive}");
        }
    }

    private void Update()
    {
        if (Calibrated && server != null && server.body != null && server.body.active)
        {
            Vector3 pelvisLeftPose = server.GetLandmark(Landmark.LEFT_HIP).position;
            Vector3 pelvisRightPose = server.GetLandmark(Landmark.RIGHT_HIP).position;
            Vector3 currentPosition = transform.position;
            Vector3 pelvisPos = (pelvisLeftPose + pelvisRightPose) * 0.5f;
            transform.position = new Vector3(pelvisPos.x, currentPosition.y, pelvisPos.z);
        }

        // Ajustar la verticalidad (desplazamiento para que quede en suelo)
        if (parentCalibrationData.Count > 0)
        {
            float footYTarget = float.MaxValue;
            RaycastHit hit;

            // Check left foot ground distance
            if (Physics.Raycast(animator.GetBoneTransform(HumanBodyBones.LeftFoot).position, Vector3.down, out hit, 100f, ground, QueryTriggerInteraction.Ignore))
            {
                footYTarget = Mathf.Min(footYTarget, hit.point.y + footGroundOffset);
            }
            // Check right foot ground distance
            if (Physics.Raycast(animator.GetBoneTransform(HumanBodyBones.RightFoot).position, Vector3.down, out hit, 100f, ground, QueryTriggerInteraction.Ignore))
            {
                footYTarget = Mathf.Min(footYTarget, hit.point.y + footGroundOffset);
            }

            // Solo si detectamos suelo
            if (footYTarget != float.MaxValue)
            {
                Vector3 pos = transform.position;
                pos.y = Mathf.Lerp(pos.y, footYTarget, Time.deltaTime * 5f); // interpola para suavizar
                transform.position = pos;
            }
        }


        // Aplicar rotaciones de huesos seg�n calibraci�n
        foreach (var iList in parentCalibrationData)
        {
            foreach (var i in iList.Value)
            {
                Quaternion deltaRotTracked = Quaternion.FromToRotation(i.initialDir, i.CurrentDirection);
                i.parent.rotation = deltaRotTracked * i.initialRotation;
            }
        }

        // Gesti�n especial de la columna vertebral y rotaci�n general del avatar
        if (parentCalibrationData.Count > 0)
        {
            Vector3 hd = head.CurrentDirection;
            Quaternion headr = Quaternion.FromToRotation(head.initialDir, hd);
            Quaternion twist = Quaternion.FromToRotation(hipsTwist.initialDir, Vector3.Slerp(hipsTwist.initialDir, hipsTwist.CurrentDirection, .25f));
            Quaternion updown = Quaternion.FromToRotation(spineUpDown.initialDir, Vector3.Slerp(spineUpDown.initialDir, spineUpDown.CurrentDirection, .25f));

            Quaternion h = updown * updown * updown * twist * twist;
            Quaternion s = h * twist * updown;
            Quaternion c = s * twist * twist;
            float speed = 10f;
            hipsTwist.Tick(h * hipsTwist.initialRotation, speed);
            spineUpDown.Tick(s * spineUpDown.initialRotation, speed);
            chest.Tick(c * chest.initialRotation, speed);
            head.Tick(updown * twist * headr * head.initialRotation, speed);

            Vector3 d = Vector3.Slerp(hipsTwist.initialDir, hipsTwist.CurrentDirection, .25f);
            d.y *= 0.5f;
            Quaternion deltaRotTracked = Quaternion.FromToRotation(hipsTwist.initialDir, d);
            targetRot = deltaRotTracked * initialRotation;
            transform.rotation = Quaternion.Lerp(transform.rotation, targetRot, Time.deltaTime * speed);
        }
    }




}
