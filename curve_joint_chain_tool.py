import maya.cmds as cmds
import math
import re

class CurveToRigTool():
    def __init__(self):
        self.window_name = "CurveToRigWin"
        self.title = "Curve to Rig Tool"
        self.size = (300, 820)
        
        if cmds.window(self.window_name, exists=True):
            cmds.deleteUI(self.window_name)
            
        self.create_ui()
        
    def create_ui(self):
        self.window = cmds.window(self.window_name, title=self.title, widthHeight=self.size)
        main_layout = cmds.columnLayout(adjustableColumn=True, rowSpacing=10, columnOffset=["both", 10])
        
        # colors
        col_gen = [0.4, 0.6, 0.4] 
        col_util = [0.35, 0.4, 0.45] 
        col_reset = [0.4, 0.4, 0.4]  
        
        # JOINT GENERATION 
        cmds.frameLayout(label="1. Generate Joint Chain", collapsable=False, marginHeight=5, parent=main_layout)
        col1 = cmds.columnLayout(adjustableColumn=True, rowSpacing=5)
        
        cmds.text(label="Select a NURBS curve:", align="left", parent=col1)
        
        self.joints_count_field = cmds.intSliderGrp(
            label="Joint Count", field=True, minValue=2, maxValue=100, value=10,
            columnWidth3=[80, 50, 150], parent=col1
        )
        
        self.gen_primary_axis = cmds.radioButtonGrp(
            label='Primary Axis', labelArray3=['X', 'Y', 'Z'], numberOfRadioButtons=3, select=1,
            columnWidth4=[80, 50, 50, 50], parent=col1
        )
        
        cmds.button(label="Generate Chain", command=self.generate_chain, height=30, backgroundColor=col_gen, parent=col1)
        cmds.setParent(main_layout)

        # RIG SELECTION 
        cmds.frameLayout(label="2. Rig Selection", collapsable=False, marginHeight=5, parent=main_layout)
        col2 = cmds.columnLayout(adjustableColumn=True, rowSpacing=5)
        
        cmds.text(label="Select the START joint of the chain:", align="left", parent=col2)
        
        cmds.rowLayout(numberOfColumns=2, columnWidth2=[200, 80], adjustableColumn=1, parent=col2)
        self.rig_offset_axis = cmds.radioButtonGrp(
            label='Offset Axis', labelArray3=['X', 'Y', 'Z'], numberOfRadioButtons=3, select=2,
            columnWidth4=[80, 40, 40, 40]
        )
        self.neg_axis_check = cmds.checkBox(label="Negative", value=False)
        cmds.setParent(col2)
        
        cmds.rowLayout(numberOfColumns=2, columnWidth2=[140, 140], columnAttach=[1, 'both', 0], adjustableColumn=2, parent=col2)
        cmds.button(label="IK RP (Select)", command=self.rig_selected_joint, height=30, backgroundColor=col_util)
        cmds.button(label="IK RP (Auto Mid)", command=self.rig_middle_joint, height=30, backgroundColor=col_util)
        cmds.setParent(col2)

        # spline IK
        cmds.separator(style='in', height=15)
        cmds.text(label="Spline Settings:", align="left", font="boldLabelFont")

        self.spline_count_slider = cmds.intSliderGrp(
            label="Spline Ctrls", field=True, minValue=3, maxValue=10, value=4,
            columnWidth3=[80, 50, 150],
            annotation="Number of controls to drive the spline."
        )

        self.ctrl_size_slider = cmds.floatSliderGrp(
            label="Ctrl Size", field=True, minValue=0.1, maxValue=5.0, value=1.0, precision=2,
            columnWidth3=[80, 50, 150],
            annotation="Scale multiplier for the controls"
        )
        
        cmds.button(label="Rig as Spline IK", command=self.rig_spline_chain, height=40, backgroundColor=col_gen)
        cmds.setParent(col2)
        cmds.setParent(main_layout)

        # UTILITIES 
        cmds.frameLayout(label="3. Utilities", collapsable=False, marginHeight=5, parent=main_layout)
        col3 = cmds.columnLayout(adjustableColumn=True, rowSpacing=5)

        cmds.button(label="Reset Selected Controls", command=self.reset_controls, height=30, backgroundColor=col_reset)
        
        cmds.separator(style='in', height=10)
        
        cmds.text(label="Control Visibility:", align="left", font="smallPlainLabelFont")
        cmds.rowLayout(numberOfColumns=3, columnWidth3=[100, 90, 90], adjustableColumn=1, parent=col3)
        self.vis_filter_field = cmds.textField(placeholderText="Filter (e.g. 'hair')")
        cmds.button(label="Show Groups", command=lambda x: self.toggle_control_groups(True), height=25, backgroundColor=col_util)
        cmds.button(label="Hide Groups", command=lambda x: self.toggle_control_groups(False), height=25, backgroundColor=col_util)
        cmds.setParent(col3)

        cmds.separator(style='in', height=10)

        cmds.text(label="Control Selection:", align="left", font="smallPlainLabelFont")
        cmds.rowLayout(numberOfColumns=3, columnWidth3=[100, 90, 90], adjustableColumn=1, parent=col3)
        self.sel_filter_field = cmds.textField(placeholderText="Filter (e.g. 'tail')")
        cmds.button(label="Select Ctrls", command=self.select_controls_via_offset, height=25, backgroundColor=col_util)
        cmds.button(label="Deselect", command="cmds.select(clear=True)", height=25, backgroundColor=col_util)
        cmds.setParent(col3)
        
        cmds.separator(style='in', height=10)
        
        cmds.rowLayout(numberOfColumns=2, columnWidth2=[180, 100], adjustableColumn=1, parent=col3)
        self.parent_target_field = cmds.textField(placeholderText="Target Group Name")
        cmds.button(label="Parent To...", command=self.parent_to_group, height=30, backgroundColor=col_util)
        
        cmds.setParent(col3)

        #  FALLOFF CONTROLLER 
        cmds.separator(style='in', height=10)
        cmds.text(label="Spline Falloff Controllers:", align="left", font="boldLabelFont")
        
        cmds.rowLayout(numberOfColumns=2, columnWidth2=[140, 140], adjustableColumn=1, parent=main_layout)
        cmds.button(label="Create Falloff Controller", command=self.create_falloff_master, height=35, backgroundColor=col_gen)
        cmds.button(label="Create Global Falloff Controller Master", command=self.create_global_falloff_master, height=35, backgroundColor=col_gen)
        cmds.setParent(main_layout)

        cmds.showWindow(self.window)

    # HELPER FUNCTIONS
    def set_color(self, object_name, color_index=17):
        # quick shape override for color
        try:
            shapes = cmds.listRelatives(object_name, shapes=True, fullPath=True)
            if shapes:
                for shape in shapes:
                    cmds.setAttr(f"{shape}.overrideEnabled", 1)
                    cmds.setAttr(f"{shape}.overrideColor", color_index)
        except Exception as e: 
            print(f"Warning: Color set failed on {object_name}: {e}")

    def create_wireframe_sphere(self, name, radius):
        # just a standard 3-ring sphere shape
        cmds.select(clear=True)
        c1 = cmds.circle(normal=(1, 0, 0), radius=radius, ch=False)[0]
        c2 = cmds.circle(normal=(0, 1, 0), radius=radius, ch=False)[0]
        c3 = cmds.circle(normal=(0, 0, 1), radius=radius, ch=False)[0]
        
        c2_shape = cmds.listRelatives(c2, shapes=True)[0]
        c3_shape = cmds.listRelatives(c3, shapes=True)[0]
        cmds.parent(c2_shape, c1, relative=True, shape=True)
        cmds.parent(c3_shape, c1, relative=True, shape=True)
        
        cmds.delete(c2, c3)
        return cmds.rename(c1, name)

    def create_offset_group(self, ctrl):
        # zero out the control by parenting it to a matched group
        grp_name = f"{ctrl}_Offset_Grp"
        grp = cmds.group(empty=True, name=grp_name)
        cmds.matchTransform(grp, ctrl)
        cmds.parent(ctrl, grp)
        return grp

    def get_root_joint(self, joint_node):
        # walk up the hierarchy to find the top-most joint
        current_node = joint_node
        while True:
            parent = cmds.listRelatives(current_node, parent=True, type='joint')
            if not parent:
                break
            current_node = parent[0]
        return current_node

    def get_distance(self, obj1, obj2):
        pos1 = cmds.xform(obj1, q=True, ws=True, t=True)
        pos2 = cmds.xform(obj2, q=True, ws=True, t=True)
        return math.sqrt(sum([(a - b) ** 2 for a, b in zip(pos1, pos2)]))

    # UTILITIES
    def reset_controls(self, *args):
        sel = cmds.ls(selection=True)
        if not sel:
            cmds.warning("Nothing selected to reset.")
            return

        # grab transforms, including children, but ignore joints
        objects_to_reset = sel + (cmds.listRelatives(sel, allDescendents=True, type='transform') or [])
        
        count = 0
        for obj in set(objects_to_reset):
            if cmds.nodeType(obj) == 'joint': continue

            # zero out translation/rotation
            for attr in ['tx', 'ty', 'tz', 'rx', 'ry', 'rz']:
                try:
                    if cmds.getAttr(f"{obj}.{attr}", settable=True):
                        cmds.setAttr(f"{obj}.{attr}", 0)
                except: pass
            
            # reset scale to 1
            for attr in ['sx', 'sy', 'sz']:
                try:
                    if cmds.getAttr(f"{obj}.{attr}", settable=True):
                        cmds.setAttr(f"{obj}.{attr}", 1)
                except: pass
            count += 1
            
        print(f"Reset {count} objects.")

    def parent_to_group(self, *args):
        sel = cmds.ls(selection=True)
        if not sel:
            cmds.warning("Select objects to parent first.")
            return

        target_group = cmds.textField(self.parent_target_field, query=True, text=True)
        
        if not target_group or not cmds.objExists(target_group):
            cmds.warning(f"Target group '{target_group}' invalid or not found.")
            return

        try:
            cmds.parent(sel, target_group)
            print(f"Parented {len(sel)} objects to '{target_group}'.")
        except Exception as e:
            cmds.warning(f"Parenting failed: {e}")

    def toggle_control_groups(self, state):
        # toggles visibility based on naming convention
        filter_text = cmds.textField(self.vis_filter_field, query=True, text=True)
        pattern = f"*{filter_text}*Controls_Grp" if filter_text else "*Controls_Grp"
            
        found_groups = cmds.ls(pattern, type='transform')
        
        if not found_groups:
            cmds.warning(f"No groups found for: {pattern}")
            return
            
        for grp in found_groups:
            cmds.setAttr(f"{grp}.visibility", 1 if state else 0)
            
        print(f"{'Shown' if state else 'Hidden'} {len(found_groups)} groups.")

    def select_controls_via_offset(self, *args):
        # grabs the child of the offset group to select the actual control
        filter_text = cmds.textField(self.sel_filter_field, query=True, text=True)
        pattern = f"*{filter_text}*Offset_Grp" if filter_text else "*Offset_Grp"
            
        found_offsets = cmds.ls(pattern, type='transform')
        
        if not found_offsets:
            cmds.warning(f"No offsets found for: {pattern}")
            return
        
        controls_to_select = []
        for offset in found_offsets:
            children = cmds.listRelatives(offset, children=True, type='transform')
            if children:
                controls_to_select.append(children[0])
            
        if controls_to_select:
            cmds.select(controls_to_select)
            print(f"Selected {len(controls_to_select)} controls.")

    def create_falloff_master(self, *args):
        """
        Generates a master control for a single strand.
        Calculates linear falloff weights based on index in chain.
        """
        sel = cmds.ls(selection=True)
        controls = [obj for obj in sel if "SplineCtrl" in obj]
        
        if len(controls) < 2:
            cmds.warning("Need at least 2 'SplineCtrl' objects selected.")
            return

        # sort by suffix index to ensure root to tip order
        try:
            controls.sort(key=lambda x: int(re.search(r'(\d+)$', x).group(1)))
        except AttributeError:
            cmds.error("Controls need numeric suffix (e.g. _01) for sorting.")
            return

        # figure out naming based on selection
        first_ctrl = controls[0]
        prefix = first_ctrl.split('SplineCtrl')[0].strip('_') or "Hair"
            
        master_ctrl_name = f"{prefix}_SplineFalloff_Ctrl"
        
        # handle duplicate names
        count = 1
        base_name = master_ctrl_name
        while cmds.objExists(master_ctrl_name):
            master_ctrl_name = f"{base_name}_{count}"
            count += 1

        # build master ctrl
        master_grp = cmds.group(empty=True, name=master_ctrl_name + "_Grp")
        master_ctrl = cmds.circle(name=master_ctrl_name, normal=(0, 1, 0), radius=6)[0]
        cmds.parent(master_ctrl, master_grp)

        # snap to tip
        cmds.matchTransform(master_grp, controls[-1])
        self.set_color(master_ctrl, 13)

        org_group_name = "Spline_Falloff_Controllers"
        if not cmds.objExists(org_group_name):
            cmds.group(empty=True, name=org_group_name)
        cmds.parent(master_grp, org_group_name)

        # iterate and connect
        num_controls = len(controls)
        print(f"--- Linking {master_ctrl_name} ---")

        for i, ctrl in enumerate(controls):
            # 0.0 at root, 1.0 at tip
            weight = float(i) / float(num_controls - 1)
            
            # skip root
            if weight <= 0.001: continue

            # grab the offset group to inject our driven group inside it
            parents = cmds.listRelatives(ctrl, parent=True)
            if not parents: continue
            existing_offset = parents[0]

            # inject "driven" group if not present
            driven_grp_name = f"{ctrl}_Driven_Grp"
            
            if driven_grp_name in parents:
                 driven_grp = parents[0] 
            else:
                driven_grp = cmds.group(empty=True, name=driven_grp_name)
                cmds.parent(driven_grp, existing_offset)
                
                # zero local space
                cmds.setAttr(f"{driven_grp}.translate", 0, 0, 0)
                cmds.setAttr(f"{driven_grp}.rotate", 0, 0, 0)
                
                # re-parent control
                cmds.parent(ctrl, driven_grp)

            # connect math: master * weight -> driven group
            # translation
            md_trans = cmds.createNode('multiplyDivide', name=f"{ctrl}_Trans_MD")
            cmds.setAttr(f"{md_trans}.operation", 1) 
            
            cmds.connectAttr(f"{master_ctrl}.translate", f"{md_trans}.input1")
            for axis in 'XYZ': cmds.setAttr(f"{md_trans}.input2{axis}", weight)
            
            cmds.connectAttr(f"{md_trans}.output", f"{driven_grp}.translate", force=True)
            
            # rotation
            md_rot = cmds.createNode('multiplyDivide', name=f"{ctrl}_Rot_MD")
            cmds.setAttr(f"{md_rot}.operation", 1)
            
            cmds.connectAttr(f"{master_ctrl}.rotate", f"{md_rot}.input1")
            for axis in 'XYZ': cmds.setAttr(f"{md_rot}.input2{axis}", weight)
            
            cmds.connectAttr(f"{md_rot}.output", f"{driven_grp}.rotate", force=True)

        cmds.select(master_ctrl)
        print(f"Created {master_ctrl_name}")

    def create_global_falloff_master(self, *args):
        """
        Creates a 'Global' master that drives all existing Falloff Controllers.
        Uses PlusMinusAverage injection to prevent jumping/double transforms.
        """
        org_group_name = "Spline_Falloff_Controllers"
        
        if not cmds.objExists(org_group_name):
            cmds.warning("No Falloff Controllers found.")
            return

        # find the actual controllers inside the organization group
        master_grps = cmds.listRelatives(org_group_name, children=True, type="transform") or []
        
        sub_controllers = []
        for grp in master_grps:
            children = cmds.listRelatives(grp, children=True, type="transform")
            if children: sub_controllers.append(children[0])

        if not sub_controllers:
            cmds.warning("Group is empty.")
            return

        global_ctrl_name = "Global_Spline_Falloff_Master"
        if cmds.objExists(global_ctrl_name):
            cmds.warning("Global Master already exists.")
            return

        # calculate average center point
        avg_pos = [0.0, 0.0, 0.0]
        for ctrl in sub_controllers:
            pos = cmds.xform(ctrl, query=True, translation=True, worldSpace=True)
            avg_pos = [sum(x) for x in zip(avg_pos, pos)]
        
        avg_pos = [x / len(sub_controllers) for x in avg_pos]

        # create group at world center, control at local zero
        # this prevents the control values from jumping on creation
        global_grp = cmds.group(empty=True, name=global_ctrl_name + "_Grp")
        cmds.xform(global_grp, translation=avg_pos, worldSpace=True)

        global_ctrl = cmds.circle(name=global_ctrl_name, normal=(0, 1, 0), radius=12)[0]
        cmds.parent(global_ctrl, global_grp)
        
        # ensure identity
        cmds.setAttr(f"{global_ctrl}.translate", 0, 0, 0)
        cmds.setAttr(f"{global_ctrl}.rotate", 0, 0, 0)
        self.set_color(global_ctrl, 17) 
        
        # add influence attribute
        attr_name = "Global_Influence"
        cmds.addAttr(global_ctrl, longName=attr_name, attributeType='float', min=0, max=1, defaultValue=1, keyable=True)

        # create global multipliers (movement * influence)
        # one for trans, one for rot
        glob_trans_mult = cmds.createNode('multiplyDivide', name="Global_Trans_Influence_MD")
        cmds.connectAttr(f"{global_ctrl}.translate", f"{glob_trans_mult}.input1")
        for axis in 'XYZ': cmds.connectAttr(f"{global_ctrl}.{attr_name}", f"{glob_trans_mult}.input2{axis}")

        glob_rot_mult = cmds.createNode('multiplyDivide', name="Global_Rot_Influence_MD")
        cmds.connectAttr(f"{global_ctrl}.rotate", f"{glob_rot_mult}.input1")
        for axis in 'XYZ': cmds.connectAttr(f"{global_ctrl}.{attr_name}", f"{glob_rot_mult}.input2{axis}")

        print(f"--- Injecting Global Master into {len(sub_controllers)} strands ---")

        for sub_ctrl in sub_controllers:
            # parent constraint the group
            parent_grp = cmds.listRelatives(sub_ctrl, parent=True)[0]
            cmds.parentConstraint(global_ctrl, parent_grp, maintainOffset=True)

            # plusminusaverage
            # new formula driven_grp = (submaster local) + (global master * influence)
            
            sum_trans = cmds.createNode('plusMinusAverage', name=f"{sub_ctrl}_Sum_Trans_PMA")
            sum_rot = cmds.createNode('plusMinusAverage', name=f"{sub_ctrl}_Sum_Rot_PMA")
            
            # input 3d[0] = sub master
            cmds.connectAttr(f"{sub_ctrl}.translate", f"{sum_trans}.input3D[0]")
            cmds.connectAttr(f"{sub_ctrl}.rotate", f"{sum_rot}.input3D[0]")
            
            # input 3d[1] = global master
            cmds.connectAttr(f"{glob_trans_mult}.output", f"{sum_trans}.input3D[1]")
            cmds.connectAttr(f"{glob_rot_mult}.output", f"{sum_rot}.input3D[1]")
            
            # find existing connection to falloff nodes and hijack it
            # look for connections to multiplydivide nodes (the per-joint falloff calculations)
            connected_mds = cmds.listConnections(f"{sub_ctrl}.translate", type='multiplyDivide', plugs=True) or []
            
            for plug in connected_mds:
                node = plug.split('.')[0]
                if "_Trans_MD" in node:
                    cmds.connectAttr(f"{sum_trans}.output3D", plug, force=True)

            connected_rot_mds = cmds.listConnections(f"{sub_ctrl}.rotate", type='multiplyDivide', plugs=True) or []
            for plug in connected_rot_mds:
                node = plug.split('.')[0]
                if "_Rot_MD" in node:
                    cmds.connectAttr(f"{sum_rot}.output3D", plug, force=True)

        cmds.select(global_ctrl)
        print("Global Master connected.")

    # JOINTS
    def generate_chain(self, *args):
        count = cmds.intSliderGrp(self.joints_count_field, query=True, value=True)
        axis_idx = cmds.radioButtonGrp(self.gen_primary_axis, query=True, select=True)
        axis_map = {1: 'xyz', 2: 'yxz', 3: 'zxy'}
        orient_str = axis_map.get(axis_idx, 'xyz')
        
        selection = cmds.ls(selection=True)
        if not selection:
            cmds.warning("Select a curve first.")
            return
            
        curve_node = selection[0]
        # validate selection is a curve
        shapes = cmds.listRelatives(curve_node, shapes=True) or []
        if not shapes or cmds.nodeType(shapes[0]) != "nurbsCurve":
            cmds.warning("Selection is not a valid NURBS curve.")
            return

        # duplicate curve to rebuild it (clean topo for even joint spacing)
        temp_curve = cmds.duplicate(curve_node, name="TEMP_CURVE_PROCESSING")[0]
        cmds.rebuildCurve(temp_curve, ch=False, rpo=1, rt=0, end=1, kr=0, kcp=0, kep=1, kt=0, s=count*4, d=3, tol=0.01)

        cmds.select(clear=True)
        created_joints = []
        
        for i in range(count):
            u_param = 0.5 if count == 1 else float(i) / float(count - 1)
            
            pos = cmds.pointOnCurve(temp_curve, pr=u_param, top=True, position=True)
            jnt = cmds.joint(p=pos, name=f"curveJnt_{i+1:02d}")
            created_joints.append(jnt)
            
        # orient joints
        if len(created_joints) > 1:
            cmds.joint(created_joints[0], edit=True, orientJoint=orient_str, secondaryAxisOrient='yup', children=True, zeroScaleOrient=True)
            # zero out the tip joint orientation
            cmds.joint(created_joints[-1], edit=True, orientJoint='none', zeroScaleOrient=True)
            cmds.setAttr(f"{created_joints[-1]}.jointOrient", 0, 0, 0)

        cmds.delete(temp_curve)
        
        if created_joints:
            cmds.select(created_joints[0])
            print(f"Chain created: {len(created_joints)} joints.")

    # SPLINE RIG
    def rig_spline_chain(self, *args):
        print("--- Building Spline Rig ---")
        sel = cmds.ls(selection=True, type='joint')
        if not sel:
            cmds.warning("Select the start joint.")
            return
            
        start_joint = sel[0]
        target_ctrl_count = cmds.intSliderGrp(self.spline_count_slider, query=True, value=True)
        size_multiplier = cmds.floatSliderGrp(self.ctrl_size_slider, query=True, value=True)

        descendants = cmds.listRelatives(start_joint, allDescendents=True, type='joint') or []
        if not descendants: return
        end_joint = descendants[0]

        chain_len = self.get_distance(start_joint, end_joint)
        ctrl_radius = (chain_len / 12.0) * size_multiplier

        # create IK handle and curve
        ik_name = f"{start_joint}_SplineIK"
        ik_results = cmds.ikHandle(startJoint=start_joint, endEffector=end_joint, solver='ikSplineSolver', 
                                   createCurve=True, parentCurve=False, simplifyCurve=False, name=ik_name)
        ik_handle = ik_results[0]
        ik_curve = cmds.rename(ik_results[2], f"{start_joint}_SplineCrv")
        
        # stop double transforms on the curve
        cmds.setAttr(f"{ik_curve}.inheritsTransform", 0)
        cmds.setAttr(f"{ik_curve}.visibility", 0)
        cmds.setAttr(f"{ik_handle}.visibility", 0)

        # smooth curve
        cmds.rebuildCurve(ik_curve, ch=False, rpo=1, rt=0, end=1, kr=0, kcp=0, kep=1, kt=0, s=60, d=3, tol=0.01)

        # groups for organization
        ctrl_grp = cmds.group(empty=True, name=f"{start_joint}_Controls_Grp")
        driver_joints_grp = cmds.group(empty=True, name=f"{start_joint}_DriverJnts_Grp")
        cmds.setAttr(f"{driver_joints_grp}.visibility", 0)

        driver_joints = []
        
        for i in range(target_ctrl_count):
            u_param = float(i) / float(target_ctrl_count - 1)
            pos = cmds.pointOnCurve(ik_curve, pr=u_param, top=True, position=True)
            
            ctrl_name = f"{start_joint}_SplineCtrl_{i+1:02d}"
            
            # create control
            ctrl = self.create_wireframe_sphere(name=ctrl_name, radius=ctrl_radius)
            self.set_color(ctrl, 17) 
            cmds.xform(ctrl, translation=pos, worldSpace=True)
            
            offset_grp = self.create_offset_group(ctrl)
            
            # create driver joint (hidden bones that skin the curve)
            cmds.select(clear=True)
            drv_jnt = cmds.joint(p=pos, name=f"{start_joint}_DriverJnt_{i+1:02d}")
            cmds.setAttr(f"{drv_jnt}.radius", 0.1) 
            cmds.setAttr(f"{drv_jnt}.drawStyle", 2) # hide

            cmds.parent(drv_jnt, ctrl)
            cmds.parent(offset_grp, ctrl_grp)
            
            driver_joints.append(drv_jnt)

        # bind curve to driver joints
        cmds.select(driver_joints)
        cmds.select(ik_curve, add=True)
        cmds.skinCluster(toSelectedBones=True, bindMethod=0, maximumInfluences=2, normalizeWeights=1, name=f"{start_joint}_SplineSkinCluster")

        # cleanup
        root_joint = self.get_root_joint(start_joint)
        mechanics_grp = cmds.group(ik_handle, ik_curve, driver_joints_grp, name=f"{start_joint}_Mechanics_Grp")
        cmds.setAttr(f"{mechanics_grp}.visibility", 0)
        
        master_grp = cmds.group(root_joint, ctrl_grp, mechanics_grp, name=f"{start_joint}_SplineRig_Grp")
        
        cmds.select(master_grp)
        print("Spline Rig Complete.")

    # IK RP RIG
    def rig_selected_joint(self, *args):
        sel = cmds.ls(selection=True, type='joint')
        if not sel: return
        self.perform_rp_rig(start_joint=sel[0], pv_anchor_joint=sel[0])

    def rig_middle_joint(self, *args):
        sel = cmds.ls(selection=True, type='joint')
        if not sel: return
        
        start_joint = sel[0]
        descendants = cmds.listRelatives(start_joint, allDescendents=True, type='joint') or []
        chain_list = [start_joint] + list(reversed(descendants))
        
        if len(chain_list) < 3:
            self.perform_rp_rig(start_joint, start_joint)
            return
            
        # find mid joint for pole vector alignment
        mid_index = len(chain_list) // 2
        middle_joint = chain_list[mid_index]
        self.perform_rp_rig(start_joint=start_joint, pv_anchor_joint=middle_joint)

    def perform_rp_rig(self, start_joint, pv_anchor_joint):
        # settings
        rig_axis_idx = cmds.radioButtonGrp(self.rig_offset_axis, query=True, select=True)
        is_negative = cmds.checkBox(self.neg_axis_check, query=True, value=True)
        
        dist = -10 if is_negative else 10
        move_vec = [0, 0, 0]
        if rig_axis_idx == 1: move_vec[0] = dist
        elif rig_axis_idx == 2: move_vec[1] = dist
        elif rig_axis_idx == 3: move_vec[2] = dist

        descendants = cmds.listRelatives(start_joint, allDescendents=True, type='joint')
        if not descendants: return
        end_joint = descendants[0]

        chain_len = self.get_distance(start_joint, end_joint)
        ctrl_rad = chain_len / 12.0

        # pole vector control
        pv_pos = cmds.xform(pv_anchor_joint, query=True, translation=True, worldSpace=True)
        pv_rot = cmds.xform(pv_anchor_joint, query=True, rotation=True, worldSpace=True)
        
        pv_ctrl = self.create_wireframe_sphere(name=f"{start_joint}_PV_Ctrl", radius=ctrl_rad * 0.7)
        cmds.xform(pv_ctrl, translation=pv_pos, worldSpace=True)
        cmds.xform(pv_ctrl, rotation=pv_rot, worldSpace=True)
        cmds.move(move_vec[0], move_vec[1], move_vec[2], pv_ctrl, relative=True, objectSpace=True)
        self.set_color(pv_ctrl, 17)
        
        pv_offset = self.create_offset_group(pv_ctrl)

        # IK handle
        ik_name = f"{start_joint}_IKHandle"
        ik_handle_data = cmds.ikHandle(startJoint=start_joint, endEffector=end_joint, solver='ikRPsolver', name=ik_name)
        ik_handle = ik_handle_data[0]
        cmds.poleVectorConstraint(pv_ctrl, ik_handle)

        # end control
        end_pos = cmds.xform(end_joint, query=True, translation=True, worldSpace=True)
        end_rot = cmds.xform(end_joint, query=True, rotation=True, worldSpace=True)

        ik_ctrl = self.create_wireframe_sphere(name=f"{end_joint}_IK_Ctrl", radius=ctrl_rad)
        cmds.xform(ik_ctrl, translation=end_pos, worldSpace=True)
        cmds.xform(ik_ctrl, rotation=end_rot, worldSpace=True)
        self.set_color(ik_ctrl, 17)
        
        ik_offset = self.create_offset_group(ik_ctrl)
        
        cmds.pointConstraint(ik_ctrl, ik_handle, maintainOffset=True)

        root_joint = self.get_root_joint(start_joint)
        items_to_group = [root_joint, pv_offset, ik_offset, ik_handle]
        master_grp = cmds.group(items_to_group, name=f"{start_joint}_Rig_Grp")

        cmds.setAttr(f"{ik_handle}.visibility", 0)
        print(f"Rig Complete: {master_grp}")

CurveToRigTool()