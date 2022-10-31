function screen2png(filename,h)
if exist('h','var')
    figure(h);
    set(h, 'InvertHardCopy', 'off');
    oldscreenunits = get(h,'Units');
    oldpaperunits = get(h,'PaperUnits');
    oldpaperpos = get(h,'PaperPosition');
    set(gcf,'Units','pixels');
    scrpos = get(h,'Position');
    newpos = scrpos/100;
    set(h,'PaperUnits','inches','PaperPosition',newpos)
    print(h,'-dpng', filename);
    drawnow
    set(h,'Units',oldscreenunits,'PaperUnits',oldpaperunits,'PaperPosition',oldpaperpos)
else
    set(gcf, 'InvertHardCopy', 'off');
    oldscreenunits = get(gcf,'Units');
    oldpaperunits = get(gcf,'PaperUnits');
    oldpaperpos = get(gcf,'PaperPosition');
    set(gcf,'Units','pixels');
    scrpos = get(gcf,'Position');
    newpos = scrpos/100;
    set(gcf,'PaperUnits','inches','PaperPosition',newpos)
    print('-dpng', filename);
    drawnow
    set(gcf,'Units',oldscreenunits,'PaperUnits',oldpaperunits,'PaperPosition',oldpaperpos)
end