' a simple Eleven program

#declare degrees$
#declare degrees
#declare units$

.start
    input "how many degrees?";degrees$
    degrees = val(degrees$)
    input "units (c/f)?";units$
    if units$ <> "c" and units$ <> "f" then .start
    gosub convert
    print "result: ";degrees;" ";units$
    end

.convert
    if units$ = "f" then convert_f_to_c
    ' convert c to f
    degrees = degrees * 9/5 + 32
    units$ = "f"
    return

.convert_f_to_c
    degrees = (degrees - 32) * 5/9
    units$ = "c"
    return
