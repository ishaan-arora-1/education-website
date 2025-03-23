import json
import cairosvg
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from python_avatars import (
    Avatar, AvatarStyle, HairType, EyebrowType, EyeType, NoseType,
    MouthType, FacialHairType, SkinColor, HairColor, AccessoryType,
    ClothingType, ClothingColor
)
from .forms import AvatarForm
from .models import Profile

from django.core.files.base import ContentFile

@login_required
def set_avatar_as_profile_pic(request):
    """Set the current avatar as the user's profile picture."""
    if request.method == "POST":
        profile = request.user.profile
        if profile.avatar_svg:
            try:
                # Convert SVG to PNG using cairosvg with explicit dimensions
                png_data = cairosvg.svg2png(
                    bytestring=profile.avatar_svg.encode('utf-8'),
                    output_width=200,
                    output_height=200
                )
                # Create a ContentFile from the PNG data
                png_file = ContentFile(png_data)
                # Delete old avatar if it exists
                if profile.avatar:
                    profile.avatar.delete(save=False)
                # Save the PNG as the profile avatar with a unique filename
                import uuid
                filename = f'avatar_{uuid.uuid4().hex[:8]}.png'
                profile.avatar.save(filename, png_file, save=True)
                messages.success(request, "Avatar set as profile picture successfully!")
            except Exception as e:
                messages.error(request, f"Error setting profile picture: {str(e)}")
        else:
            messages.error(request, "No avatar available to set as profile picture.")
    return redirect('profile')

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
                top=getattr(HairType, profile.avatar_top.upper(), HairType.SHORT_FLAT),
                eyebrows=getattr(EyebrowType, profile.avatar_eyebrows.upper(), EyebrowType.DEFAULT),
                eyes=getattr(EyeType, profile.avatar_eyes.upper(), EyeType.DEFAULT),
                nose=getattr(NoseType, profile.avatar_nose.upper(), NoseType.DEFAULT),
                mouth=getattr(MouthType, profile.avatar_mouth.upper(), MouthType.DEFAULT),
                facial_hair=getattr(FacialHairType, profile.avatar_facial_hair.upper(), FacialHairType.NONE),
                skin_color=getattr(SkinColor, profile.avatar_skin_color.upper(), SkinColor.LIGHT),
                hair_color=profile.avatar_hair_color,
                accessory=getattr(AccessoryType, profile.avatar_accessory.upper(), AccessoryType.NONE),
                clothing=getattr(ClothingType, profile.avatar_clothing.upper(), ClothingType.HOODIE),
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
        # Initialize form with current profile values
        profile = request.user.profile
        initial_data = {
            'avatar_style': profile.avatar_style,
            'avatar_background_color': profile.avatar_background_color,
            'avatar_top': profile.avatar_top,
            'avatar_eyebrows': profile.avatar_eyebrows,
            'avatar_eyes': profile.avatar_eyes,
            'avatar_nose': profile.avatar_nose,
            'avatar_mouth': profile.avatar_mouth,
            'avatar_facial_hair': profile.avatar_facial_hair,
            'avatar_skin_color': profile.avatar_skin_color,
            'avatar_hair_color': profile.avatar_hair_color,
            'avatar_accessory': profile.avatar_accessory,
            'avatar_clothing': profile.avatar_clothing,
            'avatar_clothing_color': profile.avatar_clothing_color,
        }
        form = AvatarForm(instance=profile, initial=initial_data)
    
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
            top=getattr(HairType, profile.avatar_top.upper(), HairType.SHORT_FLAT),
            eyebrows=getattr(EyebrowType, profile.avatar_eyebrows.upper(), EyebrowType.DEFAULT),
            eyes=getattr(EyeType, profile.avatar_eyes.upper(), EyeType.DEFAULT),
            nose=getattr(NoseType, profile.avatar_nose.upper(), NoseType.DEFAULT),
            mouth=getattr(MouthType, profile.avatar_mouth.upper(), MouthType.DEFAULT),
            facial_hair=getattr(FacialHairType, profile.avatar_facial_hair.upper(), FacialHairType.NONE),
            skin_color=getattr(SkinColor, profile.avatar_skin_color.upper(), SkinColor.LIGHT),
            hair_color=profile.avatar_hair_color,
            accessory=getattr(AccessoryType, profile.avatar_accessory.upper(), AccessoryType.NONE),
            clothing=getattr(ClothingType, profile.avatar_clothing.upper(), ClothingType.HOODIE),
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
                top=getattr(HairType, data.get('avatar_top', 'SHORT_FLAT').upper(), HairType.SHORT_FLAT),
                eyebrows=getattr(EyebrowType, data.get('avatar_eyebrows', 'DEFAULT').upper(), EyebrowType.DEFAULT),
                eyes=getattr(EyeType, data.get('avatar_eyes', 'DEFAULT').upper(), EyeType.DEFAULT),
                nose=getattr(NoseType, data.get('avatar_nose', 'DEFAULT').upper(), NoseType.DEFAULT),
                mouth=getattr(MouthType, data.get('avatar_mouth', 'DEFAULT').upper(), MouthType.DEFAULT),
                facial_hair=getattr(FacialHairType, data.get('avatar_facial_hair', 'NONE').upper(), FacialHairType.NONE),
                skin_color=getattr(SkinColor, data.get('avatar_skin_color', 'LIGHT').upper(), SkinColor.LIGHT),
                hair_color=data.get('avatar_hair_color', '#000000'),
                accessory=getattr(AccessoryType, data.get('avatar_accessory', 'NONE').upper(), AccessoryType.NONE),
                clothing=getattr(ClothingType, data.get('avatar_clothing', 'HOODIE').upper(), ClothingType.HOODIE),
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
