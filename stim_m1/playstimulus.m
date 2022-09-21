function playstimulus(modID)


HideCursor

switch modID
    
    case 'PG'  %Periodic Grater        

        if getParamVal('mouse_bit');
            playmanualgrater
        else
            playgrating_periodic
        end
                
    case 'FG'  %Flash Grater
        
        if getParamVal('FourierBit')
            playgrating_flashHartley
        else
            playgrating_flashCartesian
        end
        
    case 'RD'  %Raindropper
        
        playrain
        
    case 'FN'  %Filtered Noise
        
        playnoise
        
    case 'MP'  %Mapper
        
        playmapper
        
    case 'AG'   %angle
        
        if getParamVal('mouse_bit');
            playmanualangle;
        else
            playangle
        end
        
  
    case 'RK'   %random dot
        
        playrandomdot
        
        
    case 'OF'   %optic flow
        if getParamVal('mouse_bit');
            playmanualoflow;
        else
            playopticflow
        end
        
    case 'FP'   %fractal pattern for V4 retinotopy
        
        playV4Texture;
        
    case 'IM'   %images
        
        playImgTexture;
        
    case 'DG'   %dual gratings
        
        playgrating_DualGrater
        
        
    case 'TX'   %brodatz textures
        
        playBTexture;

    case 'GA'   %GA
        
        playGATexture;
        
        
    case 'RG'   %grating ramp
        
        playgrating_Ramp;
        
    case 'GM' % GA manual mapper
        
        playGAManualMapper;
end

ShowCursor
    