# Mio3 Shrink Tools

[Japanese](README.md)

A set of auxiliary tools for creating shrink shape keys for character 3D models in Blender.
Depending on the mesh shape and weights, it may not move to the desired position, so divide it into parts or adjust manually.

## What is a shrink shape key?

This shape key is implemented primarily on avatar character models that are intended to be modified.
This shape key is not for performance purposes, but is used to prevent skin penetration when modifying.

## Download

https://addon.mio3io.com/

## Features

There are automatic creation functions and tools for manual creation and adjustment

-   Automatic creation from deformation bones of the whole body

    Automatically creates shrink shape keys for the selected deformation bones.
    If no bones are selected, the visible deformation bones are targeted.
    Hide auxiliary bones and breast bones in pose mode if you want to exclude them.

-   Snap vertices to bones
-   Align edges to bone axes

Set up the armature modifier for the object to find bones from armature information and weights. Create a new shape key for the shrink shape key and then execute.

## Location

View 3D > Sidebar > Mio3 > Mio3 Shrink Tools

