"""Opt-in, in-memory EEVEE optimizations; keep rig, materials and camera animation."""
def apply(scene,profile,samples):
    if profile not in ['original','balanced']:
        raise ValueError('Unknown quality profile')
    changes={'profile':profile,'samples':samples,'baked_modifiers':0,'unshadowed_fill_lights':[]}
    scene.render.engine='BLENDER_EEVEE'
    scene.eevee.taa_render_samples=samples
    scene.eevee.use_raytracing=False
    scene.render.use_sequencer=False
    scene.render.use_compositing=False
    if profile=='original':
        return changes
    import bpy
    # Bake only static geometry modifiers, preserving the exact evaluated shape.
    # Animated rig transforms, vertices and material node trees remain untouched.
    for obj in scene.objects:
        if obj.type=='MESH' and obj.modifiers and all(m.type in ['BEVEL','WEIGHTED_NORMAL'] for m in obj.modifiers):
            if obj.data.shape_keys:
                continue
            bpy.context.view_layer.objects.active=obj
            obj.select_set(True)
            for mod in list(obj.modifiers):
                bpy.ops.object.modifier_apply(modifier=mod.name)
                changes['baked_modifiers']+=1
            obj.select_set(False)
        if obj.type=='LIGHT':
            obj.data.use_shadow_jitter=False
            obj.data.shadow_maximum_resolution=max(obj.data.shadow_maximum_resolution,.008)
            if obj.name in ['Soft face fill','Corridor depth wash']:
                obj.data.use_shadow=False
                changes['unshadowed_fill_lights'].append(obj.name)
    scene.eevee.shadow_resolution_scale=.75
    # AgX, roughness, blue/red lighting, key/rim shadows and lens animation stay authored.
    changes['shadow_resolution_scale']=.75
    return changes
