#!/usr/bin/env python

#################################
##For Syringe Pump
#################################
# New Era
import serial
import time
import re
import sys,os
import time
import re
# import serial
# import telnetlib
# import httplib
import base64
import string

import numpy as np



"""
https://syringepump.com/download/NE-1000%20Syringe%20Pump%20User%20Manual.pdf
Page 42 for all the command
Page 55 (the final page) for the conventional syringes



"""

#brand: vol ml [ diameter mm, max_rate ml/hr, min_rate ul/hr, max_rate ml/min]
dict_syringe_paras = { 'HSW': { 1: [4.69, 52.86, 0.727,  0.881],
                                3: [9.65, 223.8, 3.076, 3.73],
                                5: [12.45, 372.5, 5.119, 6.209],
                                10: [15.9, 607.6, 8.349, 10.12],
                                #20:[20.056, 966.2, 13.28, 16.1],
                                 20:[20.06, 966.2, 13.28, 16.1],
                                30: [22.9, 1260, 17.32, 21],
                                50: [29.2, 2049, 28.16, 34.15]},
                        'BD': { 1: [4.699, 53.07, 0.73,  0.884],
                                3: [8.585, 177.1, 2.434, 2.952],
                                5: [11.99, 345.5, 4.784, 5.758],
                                10: [14.43, 500.4, 6.876, 8.341],
                                20:[19.05, 872.2, 11.99, 14.53],
                                30: [21.59, 1120, 15.4, 18.67 ],
                                60: [26.59, 1699, 23.35, 28.32]},
#Hamilton gas tight
                       'HM':{ 1: [ 4.61, np.nan, np.nan, np.nan],
                              5: [ 10.3, np.nan, np.nan, np.nan ] , 
                              10: [ 14.57, np.nan, np.nan, np.nan] },
#Micro-mate
                       'MM':{ 10: [ 14.7, np.nan, np.nan, np.nan] },

                       }


def get_current_time():
    return time.time()
def get_ellapse_time(t0):
    t = time.time()
    dt = t - t0 #in second
    print('The ellapse time is: %.2f min.'%(dt/60))
    return dt



TSP = 5 #sleep time between send and read commands
#
GET_FEEDBACK = True
#GET_FEEDBACK = False


class NewEra_Pump( object ):
    def __init__( self, port, baud = 19200,timeout=1):
        self.ser = serial.Serial(port, baud, timeout=timeout)
        print('Connect to New Era pump @port=%s with baud =%s.'%(self.ser.name,baud))
        self.CR  = '\x0D'    # Carriage return
        self.STANDARD_ENCODING = 'UTF-8'

    def encode_cmd(self, cmd, pump=None):
        if pump is None:
            #formatted_command =  cmd + ' ' + self.CR
            formatted_command =  '*' + cmd  + self.CR
        else:
            formatted_command = str(pump) + cmd + ' ' + self.CR
        return str.encode(formatted_command)

    def _readline(self):
        response = self.ser.readline()
        try:
            response = response.decode(self.STANDARD_ENCODING)
        except:
            print('!'*80)
            print('Something is wrong.....')
            print('!'*80)
            reponse= None
        return response

    def cmd(self, cmd, pump=None):
        self.ser.write( self.encode_cmd(cmd,pump) )

    def find_pumps(self,tot_range= 8 ):
        '''Find all the availabe pumps'''
        pumps = []
        for i in range(tot_range):
            self.ser.write(  self.encode_cmd(cmd='ADR', pump=i) )
            time.sleep( TSP )
            #if GET_FEEDBACK:
            output = self.ser.readline().decode( 'utf-8')
            #print( output )
            if len(output)>0:
                pumps.append(i)
        self.pumps=pumps
        return pumps
    def get_direction(self, pump=0):
        '''Get the direction of the pump,
         for INF (infuse) return +
         for WDR (widthdraw) return -
         '''
        self.ser.write( self.encode_cmd(cmd='DIR', pump=pump) )
        time.sleep( TSP )
        output = self._readline() #ser.readline().decode( 'utf-8')
        if output is not None:
            if output[4:7]=='WDR':
                sign = '-'
                print('The direction for pump: %s is: %s.'%(pump, 'Withdraw'))
            else:
                sign = '+'
                print('The direction for pump: %s is: %s.'%(pump, 'Infuse'))
        return sign

    def set_direction(self, direction='INF', pump=0):
        '''Set the direction of the pump,
         for INF (infuse)
         for WDR (widthdraw)
         '''
        if direction in ['+', 'i', 'I', 1,'1', 'inf']:
            direction='INF'
        elif direction in ['-', 'w', 'W', -1,'-1', 'wdr' ]:
            direction='WDR'
        cmd = self.encode_cmd( cmd='DIR%s'%direction, pump=pump)
        self.ser.write( cmd )
        if GET_FEEDBACK:
            time.sleep( TSP )
            output = self._readline()
            if output is  None:
                print ( 'set_rate not understood.' )
            else:
                print('The direction for pump: %s is: %s.'%(pump, direction ))

    def get_rate(self,pump=0):
        '''Set the rate of the pump '''
        sign = self.get_direction(  pump=pump  )
        cmd = self.encode_cmd( cmd='RAT', pump=pump)
        self.ser.write( cmd )
        time.sleep( TSP )
        output = self._readline()
        if output is  None:
            print (   'get_rate not understood.' )
        units = output[-3:-1]
        #print(units)
        rate = output[4:-3]
        if units=='NH':
            U = ''
        elif units=='UH':
            U  = ' ul/hour'
        elif units=='UM':
            U= ' ul/min'
        elif units=='MH':
            U= ' ml/hour'
        elif units=='MM':
            U= ' ml/min'
        return sign+rate + U

    def set_rate(self, flowrate, unit='UM', pump=0):
        '''Set the rate of the pump,

        Input:
            flowrate: float
            Unit:
                'UM': ul/min
                'UH': ul/min
                'MH': ml/hour
                'MM': ml/min
            pump: int
        '''
        #if flowrate!=0:
        unit += '*'
        direction = 'INF'
        if flowrate<0:
            direction = 'WDR'
        self.set_direction(  direction=direction, pump=pump)
        time.sleep(2)
        cmd = self.encode_cmd(cmd='RAT%s%s'%(abs(flowrate),unit), pump=pump)
        self.ser.write( cmd  )
        if GET_FEEDBACK:
            time.sleep( TSP )
            output = self._readline()
            if output is  None:
                print ( 'set_rate not understood.' )
            else:
                print('The flow rate of pump: %s is set as: %s %s.'%(pump,
                                                      flowrate, unit ))

    def get_diameter(self,pump=0):
        '''Get syringe diameter of pump '''
        cmd = self.encode_cmd(cmd='DIA', pump=pump)
        self.ser.write(cmd)
        time.sleep( TSP )
        output = self._readline()
        if output is  None:
            print ( ' get_diameter not understood.' )
        else:
            dia = output[4:-1]
            print( 'The syringe diameter of pump: %s is %s.'%( pump,dia )   )
            return dia
    def set_diameter(self,dia, pump = 0):
        '''Set syringe diameter of pump '''
        cmd = self.encode_cmd(cmd='DIA %s'%dia, pump=pump)
        self.ser.write(cmd)
        if GET_FEEDBACK:
            time.sleep( TSP )
            output = self._readline()
            if output is  None:
                print (  ' from set_diameter not understood.' )
            else:
                print( 'The syringe diameter of pump: %s is set as %s.'%( pump,dia ))

    def get_volume(self,pump=0):
        '''Get maximum volume setpoint of pump '''
        cmd = self.encode_cmd(cmd='VOL', pump=pump)
        self.ser.write(cmd)
        time.sleep( TSP )
        output = self._readline()
        if output is  None:
            print ( ' from get_volume not understood.' )
        else:
            vol = output[4:-3]
            unit = output[-3:-1]
            print( 'The maximum volume setpoint of pump: %s is %s %s.'%( pump,vol, unit ))
            return float(vol), unit
    def set_volume_unit(self,  unit='UL', pump = 0):
        '''Set volume unit of pump
          Unit: UL, ML,

        '''
        output = self._readline()
        cmd = self.encode_cmd(cmd='VOL %s'%(unit), pump=pump)
        self.ser.write(cmd)

        time.sleep( TSP )
        output = self._readline()
        if output is  None:
            print (  ' from set_volume not understood.' )
        else:
            print( 'The maximum volume setpoint of pump: %s is set as %s %s.'%( pump,vol, unit ))
    def set_volume(self,vol, unit='UL', pump = 0):
        '''Set maximum volume setpoint of pump
          Unit: UL, ML,

        '''
        cmd = self.encode_cmd(cmd='VOL %s'%(vol), pump=pump)
        self.ser.write(cmd)
        if GET_FEEDBACK:
            time.sleep( TSP )
            output = self._readline()
            cmd = self.encode_cmd(cmd='VOL %s'%(unit), pump=pump)
            self.ser.write(cmd)
            output = self._readline()
            if output is  None:
                print (  ' from set_volume not understood.' )
            else:
                print( 'The maximum volume setpoint of pump: %s is set as %s %s.'%( pump,vol, unit ))

    def get_dispense(self,   pump = 0  ):
        '''Get dispense volume of pump '''

        cmd = self.encode_cmd(cmd='DIS', pump=pump)
        self.ser.write(cmd)
        time.sleep( TSP )
        output = self._readline()
        print( output )
        dir_sign = self.get_direction( pump )
        unit = output[-3:-1 ]
        span_inf = re.search( r'I(.*)W', output ).span()
        if dir_sign=='+':
            output_=  float( output[span_inf[0]+1:span_inf[1]-1] )
            return output_, unit
        elif dir_sign == '-':
            output_= float( re.search( r'W(.*)%s'%(unit[0]),output[span_inf[0]:])[0][1:-1] )
            return output_, unit
        elif '?' in output:
            print ( output.strip()+' from get_dispense not understood.' )
        else:
            print( 'The dispense of pump: %s is %s %s.'%( pump, float(output), unit ) )


    def reset_dispense(self,   pump=0, direct=None):
        '''Reset the dispense volume.'''
        if direct is None:
            dir_sign = self.get_direction( pump )
            if dir_sign == '+':
                direct= 'INF'
            elif dir_sign == '-':
                direct=   'WDR'
        print( direct )
        cmd = self.encode_cmd(cmd='CLD %s'%direct, pump=pump)
        self.ser.write(cmd)
        if GET_FEEDBACK:
            time.sleep( TSP )
            output = self._readline()
            if output is  None:
                print (   ' from reset_dispense not understood.' )
            else:
                print( 'The dispsense volume of pump in direction: %s is reset to zero.'%(pump))

    def purge(self, pump=None):
        '''pump should be '00' or '01', which is set by
            setup on the controller pannel'''
        cmd = self.encode_cmd(cmd='PUR', pump=pump)
        self.ser.write(cmd)
        if pump is None:
            pump='All'
        print('Start purge pump: %s.'%(pump))

    def run(self, pump=None,   ):
        '''pump should be '00' or '01', which is set by
            setup on the controller pannel'''
        cmd = self.encode_cmd(cmd='RUN', pump=pump)
        self.ser.write(cmd)
        if pump is None:
            pump='All'
        print('Start run pump: %s.'%(pump))

    def start_all(self ):
        return self.run(pump=None)
    def stop_all( self ):
        '''pump should be '00' or '01', which is set by
            setup on the controller pannel'''
        return self.stop(pump=None)

    def start(self, pump=0):
        return self.run(pump=pump)
    def stop(self, pump=0):
        '''pump should be '00' or '01', which is set by
            setup on the controller pannel'''
        cmd = self.encode_cmd(cmd='STP', pump=pump)
        self.ser.write(cmd)
        if pump is None:
            pump='All'
        print('Stop pump: %s.'%(pump))

    def get_version(self):
        cmd = self.encode_cmd( cmd='ver' )
        self.ser.write(cmd)
        time.sleep( TSP )
        output = self._readline()
        if '?' in output:
            print (  cmd.strip()+' from get_version not understood.' )
        else:
            print( 'The version is: %s.'%(output))

    def reset(self, pump=0):
        #cmd = '*RESET'
        #formatted_command =  cmd + ' ' + self.CR
        #cm=str.encode(formatted_command)
        #cmd = self.encode_cmd( cmd=cmd, pump=pump )
        #self.ser.write( cmd )
        self.cmd('*RESET',pump)



'''
An example:

s = pump( )
def setp( vol=50, rate=10):
    s.set_volume(vol)
    s.set_rate(rate)
    s.reset_dispense()
#    s.run()
def start():
    s.reset_dispense()
    s.run()

def monitor():
    for i in range(50):
        print(i,s.get_dispense() )
        time.sleep(5)

def start_pump( rate ):
    s.set_rate( rate )
    s.run()
def stop_pump( ):
    s.stop()


'''
