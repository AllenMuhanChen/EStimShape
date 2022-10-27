function setSecProjectPath()
%     if ~exist('projectName','var')
%         projectName = 'epga';
%     end
%     
%     if strcmp(projectName,'epga')
%         cd (['/Users/' getenv('USER') '/Dropbox/Documents/Hopkins/NHP2PV4/projectEphysGA/src'])
%     else
%         cd /Users/Ramanujan/Dropbox/Documents/Hopkins/NHP2PV4/project2PGA/src]
%     end
    
    cd (['/Users/' getenv('USER') '/Dropbox/Documents/Hopkins/Ferret2PV1/projectGCaMPNonlinearity'])
end