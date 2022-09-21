function Im = makePerGratFrame_Ramp(sdom,tdom,i,contrast)

Pstruct = getParamStruct;


Im = cos(sdom - tdom(i));


switch Pstruct.st_profile
        
    case 'sin'
        Im = Im*contrast/100;  %[-1 1]
            
    case 'square'
        thresh = cos(Pstruct.s_duty*pi);
        Im = sign(Im-thresh);
        Im = Im*contrast/100;
            
    case 'pulse'
        thresh = cos(Pstruct.s_duty*pi);
        Im = (sign(Im-thresh) + 1)/2;
        Im = Im*contrast/100;
            
end
    



