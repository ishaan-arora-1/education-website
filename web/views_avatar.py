import json
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.http import JsonResponse
from python_avatars import (
    Avatar, AvatarStyle, HairType, EyebrowType, EyeType, NoseType,
    MouthType, FacialHairType, SkinColor, HairColor, AccessoryType,
    ClothingType, ClothingColor
)
from .forms import AvatarForm
from .models import Profile

@login_required
def customize_avatar(request):
    """View for customizing user avatar."""
    if request.method == "POST":
        form = AvatarForm(request.POST, instance=request.user.profile)
        if form.is_valid():
            profile = form.save(commit=False)
            
            # Create avatar using python_avatars
            avatar = Avatar(
                style=getattr(AvatarStyle, profile.avatar_style.upper(), AvatarStyle.CIRCLE),
                background_color=profile.avatar_background_color,
                top=getattr(HairType, profile.avatar_top.upper(), HairType.SHORT_HAIR),
                eyebrows=getattr(EyebrowType, profile.avatar_eyebrows.upper(), EyebrowType.DEFAULT),
                eyes=getattr(EyeType, profile.avatar_eyes.upper(), EyeType.DEFAULT),
                nose=getattr(NoseType, profile.avatar_nose.upper(), NoseType.DEFAULT),
                mouth=getattr(MouthType, profile.avatar_mouth.upper(), MouthType.DEFAULT),
                facial_hair=getattr(FacialHairType, profile.avatar_facial_hair.upper(), FacialHairType.NONE),
                skin_color=getattr(SkinColor, profile.avatar_skin_color.upper(), SkinColor.LIGHT),
                hair_color=profile.avatar_hair_color,
                accessory=getattr(AccessoryType, profile.avatar_accessory.upper(), AccessoryType.NONE),
                clothing=getattr(ClothingType, profile.avatar_clothing.upper(), ClothingType.SHIRT),
                clothing_color=profile.avatar_clothing_color
            )
            
            # Save SVG string
            profile.avatar_svg = avatar.render()
            profile.save()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'avatar_svg': profile.avatar_svg
                })
            return redirect('profile')
    else:
        form = AvatarForm(instance=request.user.profile)
    
    # Get available options from python_avatars
    avatar_options = {
        'styles': [style.name.lower() for style in AvatarStyle],
        'hair_styles': [style.name.lower() for style in HairType],
        'eyebrow_types': [style.name.lower() for style in EyebrowType],
        'eye_types': [style.name.lower() for style in EyeType],
        'nose_types': [style.name.lower() for style in NoseType],
        'mouth_types': [style.name.lower() for style in MouthType],
        'facial_hair_types': [style.name.lower() for style in FacialHairType],
        'skin_colors': [color.name.lower() for color in SkinColor],
        'accessory_types': [acc.name.lower() for acc in AccessoryType],
        'clothing_types': [clothing.name.lower() for clothing in ClothingType],
    }
    
    # Generate initial avatar if none exists
    profile = request.user.profile
    if not profile.avatar_svg:
        avatar = Avatar(
            style=getattr(AvatarStyle, profile.avatar_style.upper(), AvatarStyle.CIRCLE),
            background_color=profile.avatar_background_color,
            top=getattr(HairType, profile.avatar_top.upper(), HairType.SHORT_HAIR),
            eyebrows=getattr(EyebrowType, profile.avatar_eyebrows.upper(), EyebrowType.DEFAULT),
            eyes=getattr(EyeType, profile.avatar_eyes.upper(), EyeType.DEFAULT),
            nose=getattr(NoseType, profile.avatar_nose.upper(), NoseType.DEFAULT),
            mouth=getattr(MouthType, profile.avatar_mouth.upper(), MouthType.DEFAULT),
            facial_hair=getattr(FacialHairType, profile.avatar_facial_hair.upper(), FacialHairType.NONE),
            skin_color=getattr(SkinColor, profile.avatar_skin_color.upper(), SkinColor.LIGHT),
            hair_color=profile.avatar_hair_color,
            accessory=getattr(AccessoryType, profile.avatar_accessory.upper(), AccessoryType.NONE),
            clothing=getattr(ClothingType, profile.avatar_clothing.upper(), ClothingType.SHIRT),
            clothing_color=profile.avatar_clothing_color
        )
        profile.avatar_svg = avatar.render()
        profile.save()
    
    return render(request, 'avatar/customize.html', {
        'form': form,
        'avatar_options': avatar_options,
        'current_avatar': profile.avatar_svg
    })

@login_required
def preview_avatar(request):
    """AJAX endpoint for previewing avatar changes."""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            avatar = Avatar(
                style=getattr(AvatarStyle, data.get('avatar_style', 'CIRCLE').upper(), AvatarStyle.CIRCLE),
                background_color=data.get('avatar_background_color', '#FFFFFF'),
                top=getattr(HairType, data.get('avatar_top', 'SHORT_HAIR').upper(), HairType.SHORT_HAIR),
                eyebrows=getattr(EyebrowType, data.get('avatar_eyebrows', 'DEFAULT').upper(), EyebrowType.DEFAULT),
                eyes=getattr(EyeType, data.get('avatar_eyes', 'DEFAULT').upper(), EyeType.DEFAULT),
                nose=getattr(NoseType, data.get('avatar_nose', 'DEFAULT').upper(), NoseType.DEFAULT),
                mouth=getattr(MouthType, data.get('avatar_mouth', 'DEFAULT').upper(), MouthType.DEFAULT),
                facial_hair=getattr(FacialHairType, data.get('avatar_facial_hair', 'NONE').upper(), FacialHairType.NONE),
                skin_color=getattr(SkinColor, data.get('avatar_skin_color', 'LIGHT').upper(), SkinColor.LIGHT),
                hair_color=data.get('avatar_hair_color', '#000000'),
                accessory=getattr(AccessoryType, data.get('avatar_accessory', 'NONE').upper(), AccessoryType.NONE),
                clothing=getattr(ClothingType, data.get('avatar_clothing', 'SHIRT').upper(), ClothingType.SHIRT),
                clothing_color=data.get('avatar_clothing_color', '#0000FF')
            )
            return JsonResponse({
                'success': True,
                'avatar_svg': avatar.render()
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)
