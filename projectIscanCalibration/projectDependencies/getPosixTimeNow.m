function a = getPosixTimeNow()
    a = floor(posixtime(datetime('now'))*1000000);
end