using System.Collections;
using System.Collections.Generic;
using Unity.VisualScripting;
using UnityEngine;

public class InitialCalibration : MonoBehaviour
{
    //public List<Transform> bones;
    private PipeServer server;
    private float boxWidth, boxHeight, boxDepth;
    private Vector3 boxDim;
    float maxX = float.MinValue, maxY = float.MinValue, maxZ = float.MinValue;
    float minX = float.MaxValue, minY = float.MaxValue, minZ = float.MaxValue;
    public void Start()
    {
        server = FindObjectOfType<PipeServer>();
    }

    public int manualScale = 1;

    //public void CalculateBoxDimensions()
    //{
    //    for (int i = 0; i < server.LANDMARK_COUNT; i++)
    //    {
    //        if (maxX < server.GetLandmark((AIbones)i).position.x)
    //        {
    //            maxX = server.GetLandmark((AIbones)i).position.x;
    //        }
    //        if (minX > server.GetLandmark((AIbones)i).position.x)
    //        {
    //            minX = server.GetLandmark((AIbones)i).position.x;
    //        }

    //        if (maxY < server.GetLandmark((AIbones)i).position.y)
    //        {
    //            maxY = server.GetLandmark((AIbones)i).position.y;
    //        }
    //        if (minY > server.GetLandmark((AIbones)i).position.y)
    //        {
    //            minY = server.GetLandmark((AIbones)i).position.y;
    //        }

    //        if (maxZ < server.GetLandmark((AIbones)i).position.z)
    //        {
    //            maxZ = server.GetLandmark((AIbones)i).position.z;
    //        }
    //        if (minZ > server.GetLandmark((AIbones)i).position.z)
    //        {
    //            minZ = server.GetLandmark((AIbones)i).position.z;
    //        }
    //    }
    //    boxWidth = Mathf.Abs(maxX - minX);
    //    boxHeight = Mathf.Abs(maxY - minY);
    //    boxDepth = Mathf.Abs(maxZ - minZ);
    //    boxDim = new Vector3(boxWidth, boxHeight, boxDepth);
    //}
    //public void CalibrateBones(Dictionary<HumanBodyBones, List<CalibrationData>> bones)
    //{

    //    CalculateBoxDimensions();
        
    //    foreach (HumanBodyBones humanBodyBone in bones.Keys)
    //    {
    //        foreach (CalibrationData bone in bones[humanBodyBone])
    //        {
    //            //bone.child.position = server.GetLandmark((AIbones)humanBodyBone).position;
    //            bone.child.rotation = Quaternion.LookRotation(bone.tchild.position - bone.tparent.position);
    //            //(tchild.position - tparent.position).normalized;
    //        }

    //    }
    //}
}
