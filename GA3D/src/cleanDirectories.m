getPaths;
if ~exist([stimPath '/' fullFolderPath],'dir')
    mkdir([stimPath '/' fullFolderPath]);
    mkdir([stimPath '/' fullFolderPath '/thumbnails']);
    mkdir([respPath '/' fullFolderPath]);
    mkdir([secondaryPath '/resp/' fullFolderPath]);
    mkdir([secondaryPath '/stim/' fullFolderPath]);
    mkdir([secondaryPath '/stim/' fullFolderPath '/thumbnails']);
    delete([respPath '/' fullFolderPath '/*.*']);
end
