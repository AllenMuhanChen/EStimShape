function insertEyeParams(c,r,l,t,b,eye,conn)
    calibrationDegree = 5;
    
    if strcmp(eye,'left'); 
        x = 1; y = 2;
    else
        x = 3; y = 4; 
    end
    
    h0 = nanmedian(c(:,x)); v0 = nanmedian(c(:,y));
    hr = nanmedian(r(:,x)); vr = nanmedian(r(:,y));
    hl = nanmedian(l(:,x)); vl = nanmedian(l(:,y));
    hu = nanmedian(t(:,x)); vu = nanmedian(t(:,y));
    hd = nanmedian(b(:,x)); vd = nanmedian(b(:,y));
    
    sxh_r = (hr - h0) / calibrationDegree;
    sxv_r = (vr - v0) / calibrationDegree;
    sxh_l = (hl - h0) / (-calibrationDegree);
    sxv_l = (vl - v0) / (-calibrationDegree);
    syh_u = (hu - h0) / calibrationDegree;
    syv_u = (vu - v0) / calibrationDegree;
    syh_d = (hd - h0) / (-calibrationDegree);
    syv_d = (vd - v0) / (-calibrationDegree);

    sxh = (sxh_r + sxh_l) / 2.0;
    sxv = (sxv_r + sxv_l) / 2.0;
    syh = (syh_u + syh_d) / 2.0;
    syv = (syv_u + syv_d) / 2.0;
    
    name = {['xper_' eye '_iscan_eye_zero'];['xper_' eye '_iscan_eye_zero'];['xper_' eye '_iscan_mapping_algorithm_parameter'];['xper_' eye '_iscan_mapping_algorithm_parameter'];['xper_' eye '_iscan_mapping_algorithm_parameter'];['xper_' eye '_iscan_mapping_algorithm_parameter']};
    arr_ind = [0 1 0 1 2 3]';
    tstamp = getPosixTimeNow;
    tstamp = [tstamp; tstamp+1; tstamp+2; tstamp+3; tstamp+4; tstamp+5];
    val = [h0;v0;sxh;sxv;syh;syv];  

    insert(conn,'systemvar',{'name','arr_ind','tstamp','val'},table(name,arr_ind,tstamp,val));
end

