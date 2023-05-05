function jigger3DView(h,az,el)
    global KEY_IS_PRESSED
    KEY_IS_PRESSED = 0;
    set(gcf, 'KeyPressFcn', @myKeyPressFcn)

    axes(h);
    while ~KEY_IS_PRESSED
        for j = az(1):az(2)
            view(j,el(1));
            pause(0.05);
        end
        for j = az(2):-1:az(1)
            view(j,el(1));
            pause(0.05);
        end
    end
end

function myKeyPressFcn(hObject, event)
    global KEY_IS_PRESSED
    KEY_IS_PRESSED  = 1;
end

