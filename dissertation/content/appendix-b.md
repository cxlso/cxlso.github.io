# Appendix B — Open-Source Repositories and Digital Research Outputs

Table B.1 lists the principal open-source repositories and digital
research outputs developed through this dissertation. They include
computational workflows, hardware integrations, workshop resources,
scripts, and fabrication documentation intended to support inspection,
adaptation, and reuse. All repositories are available at
github.com/cxlso.

<span id="_Toc234751741" class="anchor"></span>Table B.1: Open-source
repositories and digital research outputs associated with the
dissertation.

| **Repository**                                                                | **Related chapter**     | **Short description**                                                                                                                                                                                                                                                   |
|-------------------------------------------------------------------------------|-------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Literature Graph                                                              | Chapter 2               | GitHub Pages repository hosting digital research outputs, including the interactive literature-review graph developed for the dissertation.                                                                                                                             |
| Interlocking Rib-Bending Framework                                            | Chapter 5               | Computational framework for transforming two-dimensional CNC-cut sheets into interlocking bending-active rib structures through mesh-derived geometry, adaptive kerfing, nesting, and assembly logic.                                                                   |
| Crafting Tree Forks - WORKSHOP 2025                                           | Chapter 6               | Workshop repository documenting the irregular-timber workflow developed for Crafting Tree Forks, including resources related to photogrammetry, digital cataloguing, computational joinery, robotic milling, and assembly.                                              |
| MDPH2 on UR10e                                                                | Interlude II            | Open hardware and control resources for mounting and operating a Massive Dimension MDPH2 thermoplastic extruder on a UR10e robot, including controller-box and mounting components.                                                                                     |
| WASP Clay Kit on UR10e                                                        | Interlude II            | Controller-box and mounting resources for integrating the WASP Clay Kit with a UR10e robot for clay and paste extrusion.                                                                                                                                                |
| Robotic Gripping                                                              | Interlude II            | Example workflow for integrating a custom pneumatic gripper with a robotic arm, including the actuation and control logic required for robotic gripping operations.                                                                                                     |
| Robotic Printing                                                              | Interlude II; Chapter 7 | Open-source Grasshopper definitions for robotic three-dimensional printing with a Universal Robot, developed for multiple extrusion processes and toolpath conditions.                                                                                                  |
| Pen Holders on UR10e                                                          | Interlude II            | Two simple pen-holder designs for mounting drawing tools on a UR10e robot. The repository demonstrates a minimal and accessible example of custom end-effector adaptation.                                                                                              |
| ESP-NOW with Grasshopper                                                      | Interlude II; Chapter 7 | Real-time communication pipeline between Grasshopper and ESP32 microcontrollers using wired serial communication or wireless ESP-NOW. It supports low-latency read/write operations and multi-device actuation.                                                         |
| RealSense Point Cloud Capture for Grasshopper and Blender                     | Chapter 7               | Python scripts for capturing and processing Intel RealSense point-cloud data, with integrations for Grasshopper in Rhino 8 and Blender. The repository supports real-time sensing and interoperability between depth-camera data and computational design environments. |
| UR RTDE Program Cue Loop in Grasshopper                                       | Chapter 7               | Grasshopper workflow for sequencing Universal Robot programs through RTDE state monitoring. It includes examples for dividing large three-dimensional-printing toolpaths and coordinating program execution with rail repositioning.                                    |
| Vention Linear Rail and UR Cap Grasshopper Integration                        | Chapter 7               | Example setup for controlling a Vention linear rail with a Universal Robot through the Vention URCap and the Robots Grasshopper plug-in.                                                                                                                                |
| Sequenced Robotic Toolpaths: 3D Scanning and Bio-Printing on Organic Topology | Chapter 7               | Scan-to-fabrication workflow integrating sensing, computational modeling, non-planar toolpath generation, robotic sequencing, and deposition on irregular or organic substrates.                                                                                        |

The repositories represent different levels of completeness and
technical scope. Some document complete experimental workflows, while
others isolate reusable components such as communication protocols,
controller boxes, end-effector mounts, sensing scripts, or toolpath
definitions. Their inclusion in this appendix records the digital
infrastructure developed through the dissertation and provides a stable
index through which readers can locate the corresponding technical
resources.
