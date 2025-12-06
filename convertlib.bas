.convert
    if units$ = "f" then convert_f_to_c
#ifdef DEBUG
    print "converting ";degrees;" c to f"
#endif
    ' convert c to f
    degrees = degrees * 9/5 + 32
    units$ = "f"
    return

.convert_f_to_c
#ifdef DEBUG
    print "converting ";degrees;" f to c"
#endif
    degrees = (degrees - 32) * 5/9
    units$ = "c"
    return
