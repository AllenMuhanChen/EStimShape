function makeTexture(modID)


switch modID
    
    case 'PG'  %Periodic Grater
                
        makeGratingTexture_periodic
                
    case 'FG'  %Flash Grater
        
        if getParamVal('FourierBit')
            makeGratingTexture_flash
        else
            makeGratingTexture_flashCartesian
        end
        
    case 'RD'  %Raindropper
        
        makeRainTexture
        
    case 'FN'  %Filtered Noise
        
        makeNoiseTexture        
        
    case 'MP'  %Mapper
        
        %makeMapper 
        
    case 'AG'   %Angle
        
        makeAngleTexture
        
    case 'RK'   %Random Dot
        
        makeRandomDots;
        
    case 'OF'   %Optic flow
        
        makeOpticFlow;
        
    case 'FP'  %fractal like pattern for V4 retinotopy    
        
        makeV4Texture;
        
    case 'IM'  %images  
        
        makeImgTexture;
        
    case 'DG'  %nat scenes, textures and gratings
        
        makeGratingTexture_DualGrater;
        
    case 'TX'  %brodatz textures
        
        makeBTexture;
        
    case 'GA'  %genetic algorithm
        
        makeGATexture;
        
    case 'RG'  %contrast ramp
        
        makeGrating_Ramp;
    
    case 'GM' % GA manual mapper
        
        makeGAManualMapper;
        
end

