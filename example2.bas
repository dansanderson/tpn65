' temp converter using more TPN features
' build as: python3 tpn.py example2.bas convertlib.bas

#declare degrees$
#declare degrees
#declare units$

#define DEBUG

.start
    input "how many degrees";degrees$
    degrees = val(degrees$)
    input "units (c/f)";units$
    if units$ <> "c" and units$ <> "f" then .start
    gosub convert
    print "result: ";degrees;" ";units$
    end
