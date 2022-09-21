function configurePstate(modID)


switch modID
    
    case 'PG'
        
        configPstate_perGrater
        
    case 'FG'
      
        configPstate_flashGrater
        
    case 'RD'
        
        configPstate_Rain
        
    
    case 'MP'
        
        configPstate_Mapper
        
    case 'AG'
        
        configPstate_Angle
        
    case 'RK'
        
        configPstate_RandomDot
        
    case 'OF'
        
        configPstate_OpticFlow
        
    case 'FP'
        
        configPstate_V4Texture
    
    case 'IM'
        
        configPstate_Img
        
    case 'IMGab'
        
        configPstate_Gabor
        
    case 'DG'
        
        configPstate_DualGrater
        
        
    case 'TX'
        
        configPstate_BTexture

    case 'GA'
        
        configPstate_GATexture
        
    case 'RG'
        
        configPstate_GraterRamp
        
    case 'GM'

        configPstate_GAManualMapper

end

