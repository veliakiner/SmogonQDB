from datetime import datetime

#convert date from YYYY-MM-DD-T to Date, Month, Year (in words)
#dfdsf
#dsfds
datetime
def date_convert(date):
    date=str(date)
    data=date.split('-') #year/month/day+time all separated by dash
    daydate=data[-1].split() #data[-1] is day+time, separated by a space
    day=daydate[0] #discard time, keep day
    day=day if day[0]!=0 else day[1] #otherwise single-digit days retain leading zero
    year=str(data[0]) #data is list containing the year and the month
    month=str(data[1])
    #map month numbers to their names
    months={'01':'January',
            '02':'February',
            '03':'March',
            '04':'April',
            '05':'May',
            '06':'June',
            '07':'July',
            '08':'August',
            '09':'September',
            '10':'October',
            '11':'November',
            '12':'December'}
    #adds appropriate suffix to day
    if day[-1]=='1' and int(day)%100!=11: #checks if date ends with 1 and isn't 11
        suffix='st'
    elif day[-1]=='2' and int(day)%100!=12: #checks if date ends with 1 and isn't 11
        suffix='nd'
    elif day[-1]=='3':
        suffix='rd'
    else:
        suffix='th' #including special cases 11 and 12 which were previously excluded
    return day+suffix+' '+months[month]+', '+year #returns string with date in appropriate format

#test case
#date=datetime.now()
#print date_convert(date)
