function xml = formatAsXML_javaspec(stim)
    if strcmp(stim.id.type,'blank')
        xml = '<StimSpec><stimType>BLANK</stimType></StimSpec>';
    else
        % start
        xml = ['<StimSpec>' char(10)];
        % type
        xml = [xml char(9) '<stimType>GA3D</stimType>' char(10)];
        % occluder
        xml = [xml char(9) '<occluder>' char(10)];
        xml = [xml formatAsXML_occluder(stim.occluder)];
        xml = [xml char(9) '</occluder>' char(10)];
        % masks
        xml = [xml char(9) '<masks>' char(10)];
        xml = [xml formatAsXML_mask(stim.mask)];
        xml = [xml char(9) '</masks>' char(10)];
        % shapes
        xml = [xml char(9) '<shape>' char(10)];

        xml = [xml char(9) char(9) '<pos>' char(10)];
        xml = [xml char(9) char(9) char(9) '<x>' num2str(stim.shape.x) '</x>' char(10)];
        xml = [xml char(9) char(9) char(9) '<y>' num2str(stim.shape.y) '</y>' char(10)];
        xml = [xml char(9) char(9) '</pos>' char(10)];
        xml = [xml char(9) char(9) '<size>' num2str(stim.shape.s) '</size>' char(10)];

        xml = [xml char(9) char(9) '<color>' char(10)];
        xml = [xml char(9) char(9) char(9) '<red>' num2str(stim.shape.color(1)) '</red>' char(10)];
        xml = [xml char(9) char(9) char(9) '<green>' num2str(stim.shape.color(2)) '</green>' char(10)];
        xml = [xml char(9) char(9) char(9) '<blue>' num2str(stim.shape.color(3)) '</blue>' char(10)];
        xml = [xml char(9) char(9) '</color>' char(10)];
        xml = [xml char(9) char(9) '<textureType>' stim.shape.texture '</textureType>' char(10)];
        xml = [xml char(9) char(9) '<doClouds>' bool2str(stim.shape.doClouds) '</doClouds>' char(10)];
        xml = [xml char(9) char(9) '<lowPass>' bool2str(stim.shape.lowPass) '</lowPass>' char(10)];
        xml = [xml char(9) char(9) '<saveVertSpec>' bool2str(stim.id.saveVertSpec) '</saveVertSpec>' char(10)];
        xml = [xml char(9) char(9) '<radiusProfile>' num2str(stim.id.radiusProfile) '</radiusProfile>' char(10)];
        
        xml = [xml char(9) char(9) '<tagForRand>' bool2str(stim.id.tagForRand) '</tagForRand>' char(10)];
        xml = [xml char(9) char(9) '<tagForMorph>' bool2str(stim.id.tagForMorph) '</tagForMorph>' char(10)];
        xml = [xml char(9) char(9) '<isOccluded>' bool2str(stim.id.isOccluded) '</isOccluded>' char(10)];
        
        xml = [xml char(9) char(9) '<lightingPos>' char(10)];
        xml = [xml char(9) char(9) char(9) '<x>' num2str(stim.shape.lighting(1)) '</x>' char(10)];
        xml = [xml char(9) char(9) char(9) '<y>' num2str(stim.shape.lighting(2)) '</y>' char(10)];
        xml = [xml char(9) char(9) char(9) '<z>' num2str(stim.shape.lighting(3)) '</z>' char(10)];
        xml = [xml char(9) char(9) '</lightingPos>' char(10)];
        
        xml = [xml char(9) '</shape>' char(10)];
        % end
        xml = [xml '</StimSpec>'];
    end
end

function xml = formatAsXML_occluder(occluder)
    xml = '';
    xml = [xml char(9) char(9) '<leftBottom>' char(10)];
    xml = [xml char(9) char(9) char(9) '<x>' num2str(occluder.leftBottom(1)) '</x>' char(10)];
    xml = [xml char(9) char(9) char(9) '<y>' num2str(occluder.leftBottom(2)) '</y>' char(10)];
    xml = [xml char(9) char(9) char(9) '<z>' num2str(occluder.leftBottom(3)) '</z>' char(10)];
    xml = [xml char(9) char(9) '</leftBottom>' char(10)];
    xml = [xml char(9) char(9) '<rightTop>' char(10)];
    xml = [xml char(9) char(9) char(9) '<x>' num2str(occluder.rightTop(1)) '</x>' char(10)];
    xml = [xml char(9) char(9) char(9) '<y>' num2str(occluder.rightTop(2)) '</y>' char(10)];
    xml = [xml char(9) char(9) char(9) '<z>' num2str(occluder.rightTop(3)) '</z>' char(10)];
    xml = [xml char(9) char(9) '</rightTop>' char(10)];
    xml = [xml char(9) char(9) '<color>' char(10)];
    xml = [xml char(9) char(9) char(9) '<red>' num2str(occluder.color(1)) '</red>' char(10)];
    xml = [xml char(9) char(9) char(9) '<green>' num2str(occluder.color(2)) '</green>' char(10)];
    xml = [xml char(9) char(9) char(9) '<blue>' num2str(occluder.color(3)) '</blue>' char(10)];
    xml = [xml char(9) char(9) '</color>' char(10)];

end

function xml = formatAsXML_mask(masks)
    xml = '';
    if isempty(masks)
        return;
    else
        for ii=1:length(masks)
            xml = [xml char(9) char(9) '<mask>' char(10) ...
                char(9) char(9) char(9) '<x>' num2str(masks(ii).x) '</x>' char(10) ...
                char(9) char(9) char(9) '<y>' num2str(masks(ii).y) '</y>' char(10) ...
                char(9) char(9) char(9) '<z>' num2str(masks(ii).z) '</z>' char(10) ...
                char(9) char(9) char(9) '<s>' num2str(masks(ii).s) '</s>' char(10) ...
                char(9) char(9) char(9) '<isActive>' bool2str(masks(ii).isActive) '</isActive>' char(10) ...
                char(9) char(9) '</mask>' char(10)];
        end
    end
end

function str = bool2str(val)
    if val
        str = 'true';
    else
        str = 'false';
    end
end
