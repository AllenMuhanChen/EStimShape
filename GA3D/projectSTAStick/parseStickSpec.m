
function [brfields,nComp,nJunc,nEnd,CompPts,CompunDxs,endCount,...
            jCount,rCompLines,endPlace,mAxisRad,mAxisLen,tubeMidRad,...
            compPosTang] = parseStickSpec(mAxisInfo,compPosTang,doPlot,h)

    if doPlot && ~exist('h','var'); h = gca; end
    linePlotScaler = 2;
    
    %rotate before plotting assuming rotate around x first
    ralpha = deg2rad(str2double(mAxisInfo.finalRotation.double{1}.Text));
    rbeta = deg2rad(str2double(mAxisInfo.finalRotation.double{2}.Text));
    rgamma = deg2rad(str2double(mAxisInfo.finalRotation.double{3}.Text));

    rotmat  = [cos(rbeta)*cos(rgamma), (cos(rgamma)*sin(ralpha)*sin(rbeta) - cos(ralpha)*sin(rgamma)),  (cos(ralpha)*cos(rgamma)*sin(rbeta)+ sin(ralpha)*sin(rgamma)); ...
               cos(rbeta)*sin(rgamma), (cos(ralpha)*cos(rgamma) + sin(ralpha)*sin(rbeta)*sin(rgamma)), (-cos(rgamma)*sin(ralpha)+cos(ralpha)*sin(rbeta)*sin(rgamma)); ...
              -sin(rbeta)            ,  cos(rbeta)*sin(ralpha)                                       ,   cos(ralpha)*cos(rbeta)];

%     R = makehgtform('xrotate',ralpha,'yrotate',rbeta,'zrotate',rgamma);
%     rotmat = R(1:3,1:3);


    compPosTang = parseCompPosTang(compPosTang,rotmat);
    %figuring out location of each EnPt
    nEnd = str2double(mAxisInfo.nEndPt.Text);
    for endNum = 1:nEnd
        tempEndPt =  mAxisInfo.EndPt.EndPtInfo{endNum};
        fieldNames = fieldnames(tempEndPt);

        %  fieldsStruct = getfield(tempBr,'pos');
        for allNames = 1:length(fieldNames)
            %idk about tangent and rad
            %if want to store as individual branches numbered in structure
            if strcmp('pos',fieldNames{allNames}) == 1
                % x,y,z position
                brfields.EnPts(endNum).pos(1) = str2double(tempEndPt.pos.x.Text);
                brfields.EnPts(endNum).pos(2) = str2double(tempEndPt.pos.y.Text);
                brfields.EnPts(endNum).pos(3) = str2double(tempEndPt.pos.z.Text);
                brfields.EnPts(endNum).pos = rotmat*brfields.EnPts(endNum).pos';
            else
                if strcmp('tangent',fieldNames{allNames}) ==1
                  brfields.EnPts(endNum).tangent(1) = str2double(tempEndPt.tangent.x.Text);
                  brfields.EnPts(endNum).tangent(2) = str2double(tempEndPt.tangent.y.Text);
                  brfields.EnPts(endNum).tangent(3) = str2double(tempEndPt.tangent.z.Text);
                  brfields.EnPts(endNum).tangent = rotmat*brfields.EnPts(endNum).tangent';
                else
                    eval([strcat('brfields.EnPts(',num2str(endNum),').',fieldNames{allNames}) '= structfun(@(x) str2double(x), ' strcat('tempEndPt.',fieldNames{allNames}),');']);
                end
            end
        end
        
        rEPos = brfields.EnPts(endNum).pos;
        brfields.EnPts(endNum).tangent = -brfields.EnPts(endNum).tangent;
        
        if doPlot
            plot3(h,rEPos(1),rEPos(2),rEPos(3),'r.','markersize',40*linePlotScaler);
        
            rTang = brfields.EnPts(endNum).tangent;
            rTPos = findPtAlongVect(rEPos,rTang,1.2);
%             plot3(h,[rEPos(1) rTPos(1)],[rEPos(2) rTPos(2)],[rEPos(3) rTPos(3)],'b-','linewidth',4*linePlotScaler);
            
            rRad = brfields.EnPts(endNum).rad;
            
            draw3dcircle(h,rRad,rTang,rEPos,linePlotScaler);
        end

    end

    %figuring out for each JunctionPoint
    nJunc = str2double(mAxisInfo.nJuncPt.Text);
    for juncNum = 1:nJunc
        if str2double(mAxisInfo.nJuncPt.Text) == 1
            tempJunc =  mAxisInfo.JuncPt.JuncPtInfo;
        else
            tempJunc =  mAxisInfo.JuncPt.JuncPtInfo{juncNum};
        end
        % fieldNames = fieldnames(tempJunc);
        %  fieldsStruct = getfield(tempBr,'pos');
        %if want to store as individual branches numbered in structure
        %x,y,z position from pos
        brfields.JPts(juncNum).pos(1) = str2double(tempJunc.pos.x.Text);
        brfields.JPts(juncNum).pos(2) = str2double(tempJunc.pos.y.Text);
        brfields.JPts(juncNum).pos(3) = str2double(tempJunc.pos.z.Text);
        brfields.JPts(juncNum).rad = str2double(tempJunc.rad.Text);

        %  eval([strcat('brfields.EnPts(',num2str(nEnds),').',fieldNames{allNames}) '= structfun(@(x) str2double(x), ' strcat('tempEndPt.',fieldNames{allNames}),')'])
        brfields.JPts(juncNum).pos = rotmat*brfields.JPts(juncNum).pos';
        jEPos = brfields.JPts(juncNum).pos;
        if doPlot
            plot3(h,jEPos(1),jEPos(2),jEPos(3),'r.','markersize',40*linePlotScaler);
        end

        %   plot3(brfields.JPts(nJuncs).pos(1),brfields.JPts(nJuncs).pos(2),brfields.JPts(nJuncs).pos(3),'bo');
        brfields.JPts(juncNum).uNdx = zeros(1,str2double(tempJunc.nComp.Text));
        for compIn = 2:str2double(tempJunc.nComp.Text)+1 % weird indexing so first entry always 0
            brfields.JPts(juncNum).comps(compIn-1) = (str2double(tempJunc.comp.int{compIn}.Text));
            brfields.JPts(juncNum).uNdx(compIn-1) =str2double(tempJunc.uNdx.int{compIn}.Text);
            brfields.JPts(juncNum).tang{compIn-1}(1) =str2double(tempJunc.tangent.javax_dot_vecmath_dot_Vector3d{compIn-1}.x.Text);
            brfields.JPts(juncNum).tang{compIn-1}(2) =str2double(tempJunc.tangent.javax_dot_vecmath_dot_Vector3d{compIn-1}.y.Text);
            brfields.JPts(juncNum).tang{compIn-1}(3) =str2double(tempJunc.tangent.javax_dot_vecmath_dot_Vector3d{compIn-1}.z.Text);

            brfields.JPts(juncNum).tang{compIn-1} = rotmat*brfields.JPts(juncNum).tang{compIn-1}';
            
            jTang = brfields.JPts(juncNum).tang{compIn-1};
            jTPos = findPtAlongVect(jEPos,jTang,1.2);
            if doPlot
%                 plot3(h,[jEPos(1) jTPos(1)],[jEPos(2) jTPos(2)],[jEPos(3) jTPos(3)],'b-','linewidth',4*linePlotScaler);
                
                jRad = brfields.JPts(juncNum).rad;
            
%                 draw3dcircle(h,jRad,jTang,jEPos,linePlotScaler);
            end
        end
    end
    % plot and sort by component

    nComp = str2double(mAxisInfo.nComponent.Text);
    CompPts = zeros(nComp,(nEnd+nJunc));
    CompunDxs = zeros(nComp,(nEnd+nJunc));
    for curComp = 1:nComp
        endCount(curComp) = 0;
        for endPt = 1:nEnd
            if (brfields.EnPts(endPt).comp == curComp)
                endCount(curComp) = endCount(curComp) +1;
                CompPts(curComp,endCount(curComp)) = endPt;
                CompunDxs(curComp,endCount(curComp))= brfields.EnPts(endPt).uNdx;
            end
        end
        jCount(curComp) = endCount(curComp);% if were no endCounts stil works will add if matches
        for jPt = 1:nJunc
            if (sum(brfields.JPts(jPt).comps == curComp) > 0)
                jCount(curComp) = jCount(curComp) +1;
                CompPts(curComp,jCount(curComp)) = jPt;
                CompunDxs(curComp,jCount(curComp))= brfields.JPts(jPt).uNdx(brfields.JPts(jPt).comps == curComp);
            end
        end
        bcomp(curComp) = find(CompunDxs(curComp,:) == 1);%beginning and end
        ecomp(curComp) = find(CompunDxs(curComp,:) == 51);
        if bcomp(curComp) <=endCount(curComp)
            b_pos= brfields.EnPts(CompPts(curComp,bcomp(curComp))).pos;
            endPlace(curComp) = 1;
        else
            b_pos= brfields.JPts(CompPts(curComp,bcomp(curComp))).pos;
        end
        if ecomp(curComp) <=endCount(curComp)
            e_pos= brfields.EnPts(CompPts(curComp,ecomp(curComp))).pos;
            endPlace(curComp) = 2;
        else
            e_pos= brfields.JPts(CompPts(curComp,ecomp(curComp))).pos;
        end

        CompLines{curComp} = [b_pos e_pos];
        rCompLines{curComp} = CompLines{curComp};
                
        mAxisRad(curComp) = str2double(mAxisInfo.Tube.TubeInfo{curComp}.mAxis__rad.Text);
        mAxisLen(curComp) = str2double(mAxisInfo.Tube.TubeInfo{curComp}.mAxis__arcLen.Text);
        tubeMidRad(curComp) = str2double(mAxisInfo.Tube.TubeInfo{curComp}.radInfo.double_dash_array{2}.double{2}.Text);
        
        if doPlot
            plot3(h,compPosTang(curComp).pts(:,1),compPosTang(curComp).pts(:,2),...
                compPosTang(curComp).pts(:,3),'r','linewidth',4*linePlotScaler)
        end
        
        if CompunDxs(curComp,2) == 51
            compPosTang(curComp).pts = flipud(compPosTang(curComp).pts);
            compPosTang(curComp).tang = -compPosTang(curComp).tang;
        end
        
        if doPlot
            midPos = compPosTang(curComp).pts(26,:);
            midTang = compPosTang(curComp).tang(26,:);
            tempPos = findPtAlongVect(midPos,midTang,1.2);
            % plot3(h,[midPos(1) tempPos(1)],[midPos(2) tempPos(2)],[midPos(3) tempPos(3)],'b-','linewidth',4*linePlotScaler);
            
            plot3(h,midPos(1),midPos(2),midPos(3),'r.','markersize',40*linePlotScaler);
            draw3dcircle(h,tubeMidRad(curComp),midTang,midPos,linePlotScaler);
        end
        
%         pp(1) = str2double(mAxisInfo.Tube.TubeInfo{curComp}.transRotHis__finalPos.x.Text);
%         pp(2) = str2double(mAxisInfo.Tube.TubeInfo{curComp}.transRotHis__finalPos.y.Text);
%         pp(3) = str2double(mAxisInfo.Tube.TubeInfo{curComp}.transRotHis__finalPos.z.Text);
%         ppp = rotmat*pp';
%         plot3(ppp(1),ppp(2),ppp(3),'k.','markersize',15);
%         
%         tt(1) = str2double(mAxisInfo.Tube.TubeInfo{curComp}.transRotHis__finalTangent.x.Text);
%         tt(2) = str2double(mAxisInfo.Tube.TubeInfo{curComp}.transRotHis__finalTangent.y.Text);
%         tt(3) = str2double(mAxisInfo.Tube.TubeInfo{curComp}.transRotHis__finalTangent.z.Text);
%         ttt = rotmat*tt';
%         
%         tttt = findPtAlongVect(ppp,ttt,1);
%         plot3([ppp(1) tttt(1)],[ppp(2) tttt(2)],[ppp(3) tttt(3)],'k-','linewidth',2);
    end

%     for allComps = 1:curComp
%         plot3(rCompLines{curComp}(1,:),rCompLines{curComp}(2,:),rCompLines{curComp}(3,:),'r');
%         % plot3(CompLines{allComps}(1,:),rCompLines{allComps}(2,:),rCompLines{allComps}(3,:),'b--');
%     end
end

function P5 = findPtAlongVect(screenPt,unitVec,dist)
    % find a point along a vector (vec) from origin (pt0) at a distance
    % (dist)
    unitVec = unitVec./norm(unitVec);   % normalize vector
    P5 = screenPt + unitVec.*dist;
end

function parsed = parseCompPosTang(compPosTang,rotmat)
    nComp = length(compPosTang)/52;
    parsed = struct([]);
    for compNum=1:nComp
        compIdx = (compNum*2 + (compNum-1)*50) : (50*compNum+compNum*2);
        
        parsed(compNum).curvature = compPosTang((compNum*2 + (compNum-1)*50) - 1,4);
        parsed(compNum).arcLen = compPosTang((compNum*2 + (compNum-1)*50) - 1,5);
        parsed(compNum).rad = compPosTang((compNum*2 + (compNum-1)*50) - 1,6);
        
        parsed(compNum).pts = (rotmat*compPosTang(compIdx,1:3)')';
        parsed(compNum).tang = (rotmat*compPosTang(compIdx,4:6)')';
    end
end

function draw3dcircle(h,rad,tang,center,linePlotScaler)
    % rotation vector magic for the circles
    ssc = @(v) [0 -v(3) v(2); v(3) 0 -v(1); -v(2) v(1) 0];
    RU = @(A,B) eye(3) + ssc(cross(A,B)) + ssc(cross(A,B))^2*(1-dot(A,B))/(norm(cross(A,B))^2);
    
    [xx,yy] = pol2cart(linspace(0,2*pi,100),rad*ones(1,100));
    zz = zeros(1,100);

    rotVec = RU([0 0 1],tang);
    a = rotVec * [xx; yy; zz];

    plot3(h,a(1,:)+center(1),a(2,:)+center(2),a(3,:)+center(3),'color',[255,165,0]/255,'LineWidth',5*linePlotScaler);
end