from __future__ import division
from sensl import HRMTimeAPI
import wx
import matplotlib
matplotlib.use('WxAgg')
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg, NavigationToolbar2WxAgg
import matplotlib.pyplot as plt
import numpy as np
import threading
import time
import sys
import os

''' 
Author - Daniel J. Whiting 
Date modified - 10/08/2017
Modifications/comments by Renju S. Mathew

A python GUI for performing photon count correlation measurements with
the HRMTime module manufactured by SensL.

--- Installation ---
Requires standard python 32 bit installation including numpy, matplotlib
and wx packages.

--- Usage ---
--- Changelog ---
'''

def bindata(x,y,binfac=0):
    for i in range(binfac):
        y = (y[:-1:2]+y[1::2])
        x = (x[:-1:2]+x[1::2])/2
    return x,y

class MainFrame(wx.Frame):
    def __init__(self,parent,title):
        ''' init method for main frame '''
        self.temp_output = [] # To hold count rates at each timestep
        self.t0 = 0 # time when run is started
        self.t1 = 0 # time when save happens
        
        wx.Frame.__init__(self,parent,title=title)
        
        self.HRMTime = HRMTimeAPI()
        
        ########### Init Params ###########
        self.recordinglength = 1000 # ms
        self.ncounts = 1000000
        self.dtmax = 40000 # ps # max correlation time between herald and signal
        self.dntags = 2 # number of time tags to consider for calculating the cross correlation
        self.plotbinfactor = 1 # number of time bins to combine for plot
        self.DataCollectFlag = False # Dont collect data at program start
        self.dirname = ''
        self.cumulativeflag = True #rsm
        
        ########### Right Panel ############
        self.rightpanel = wx.Panel(self,style=wx.BORDER)
        
        self.combobox = wx.ComboBox(self.rightpanel,choices=['Cross Correlation','Heralded Cross Correlation','Auto Correlation C0','Auto Correlation C1','Auto Correlation C2'],style=wx.CB_DROPDOWN)
        self.combobox.SetValue('Cross Correlation')
        self.Bind(wx.EVT_COMBOBOX, self.OnComboSelect, self.combobox)
        
        self.cumulativetickboxtextlabel = wx.StaticText(self.rightpanel,label='Cumulative mode?')
        self.cumulativetickbox = wx.CheckBox(self.rightpanel)
        self.cumulativetickbox.SetValue(True) #rsm
        self.tickboxsizer = wx.BoxSizer(wx.HORIZONTAL)
        self.tickboxsizer.Add(self.cumulativetickboxtextlabel,1,wx.EXPAND)
        self.tickboxsizer.Add(self.cumulativetickbox,0,wx.EXPAND)
        
        self.rightpaneltextctrls = []
        self.rightpaneltextlabels = []
        self.rightpaneltextctrls.append(wx.TextCtrl(self.rightpanel,value=str(self.recordinglength)))
        self.rightpaneltextlabels.append(wx.StaticText(self.rightpanel,label='Max recording time (s)'))
        self.rightpaneltextctrls.append(wx.TextCtrl(self.rightpanel,value=str(self.ncounts)))
        self.rightpaneltextlabels.append(wx.StaticText(self.rightpanel,label='Max number of counts'))        
        self.rightpaneltextctrls.append(wx.TextCtrl(self.rightpanel,value=str(self.dtmax)))
        self.rightpaneltextlabels.append(wx.StaticText(self.rightpanel,label='Max correlation time (ps)'))        
        self.rightpaneltextctrls.append(wx.TextCtrl(self.rightpanel,value=str(self.plotbinfactor)))
        self.rightpaneltextlabels.append(wx.StaticText(self.rightpanel,label='Plot binning factor'))    
        self.rightpaneltextctrls.append(wx.TextCtrl(self.rightpanel,value=str(self.dntags)))
        self.rightpaneltextlabels.append(wx.StaticText(self.rightpanel,label='# of tags per trigger'))
        
        self.applybutton = wx.Button(self.rightpanel, wx.ID_ANY, 'Apply')
        self.Bind(wx.EVT_BUTTON, self.OnApply, self.applybutton)
        
        # Create sizer
        self.rightpanelsizer = wx.BoxSizer(wx.VERTICAL)
        self.rightpanelsizer.Add(wx.StaticText(self.rightpanel,label='Settings',style=wx.ALIGN_CENTRE_HORIZONTAL),0,wx.EXPAND|wx.ALL,border=10)
        self.rightpanelsizer.Add(self.combobox,0,wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM,border=10)
        self.rightpanelsizer.Add(self.tickboxsizer,0,wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM,border=10)
        for i in range(len(self.rightpaneltextctrls)):
            self.rightpanelsizer.Add(self.rightpaneltextlabels[i],0,wx.EXPAND|wx.LEFT|wx.RIGHT,border=10)
            self.rightpanelsizer.Add(self.rightpaneltextctrls[i],0,wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM,border=10)
        self.rightpanelsizer.Add(self.applybutton,0,wx.EXPAND|wx.LEFT|wx.RIGHT,border=10)
        
        # Layout sizer
        self.rightpanel.SetSizerAndFit(self.rightpanelsizer)

        ########## Create Left Panel ##########
        self.leftpanel = wx.Panel(self)
        
        ########### Plot Panel ############
        self.plotpanel = wx.Panel(self.leftpanel)
        self.fig = plt.figure(figsize=(8,4.944),facecolor='white')

        self.canvas = FigureCanvasWxAgg(self.plotpanel, wx.ID_ANY, self.fig)
        self.navtoolbar = NavigationToolbar2WxAgg(self.canvas)

        # Create sizer
        self.plotsizer = wx.BoxSizer(wx.VERTICAL)
        self.plotsizer.Add(self.canvas, 1, wx.LEFT|wx.RIGHT|wx.GROW,border=0)
        self.plotsizer.Add(self.navtoolbar, 0, wx.LEFT|wx.RIGHT|wx.EXPAND,border=0)

        # Layout sizer
        self.plotpanel.SetSizerAndFit(self.plotsizer)
        
        ########### Top Button Panel ###########
        self.topbuttonpanel = wx.Panel(self.leftpanel)
        self.topbuttons = []
        self.topbuttons.append(wx.Button(self.topbuttonpanel, wx.ID_ANY, 'Run Once'))
        self.Bind(wx.EVT_BUTTON, self.OnRunOnce, self.topbuttons[-1])
        self.topbuttons.append(wx.Button(self.topbuttonpanel, wx.ID_ANY, 'Run Continuous'))
        self.Bind(wx.EVT_BUTTON, self.OnRunContinuous, self.topbuttons[-1])
        self.topbuttons.append(wx.Button(self.topbuttonpanel, wx.ID_ANY, 'Stop'))
        self.Bind(wx.EVT_BUTTON, self.OnStop, self.topbuttons[-1])
        self.topbuttons.append(wx.Button(self.topbuttonpanel, wx.ID_ANY, 'Save Correlation Data'))
        self.Bind(wx.EVT_BUTTON, self.OnSaveCorrelation, self.topbuttons[-1])
        
        # Create sizer
        self.topbuttonsizer = wx.BoxSizer(wx.HORIZONTAL)
        for i,button in enumerate(self.topbuttons):
            self.topbuttonsizer.Add(button, 1, wx.EXPAND)

        # Layout sizer
        self.topbuttonpanel.SetSizerAndFit(self.topbuttonsizer)
        
        ######### Left panel sizer ##########
        self.leftsizer = wx.BoxSizer(wx.VERTICAL)
        self.leftsizer.Add(self.topbuttonpanel,0,wx.EXPAND)
        self.leftsizer.Add(self.plotpanel,1,wx.EXPAND)
        self.SetSizerAndFit(self.leftsizer)
        
        ######### Top level sizer #############
        self.topsizer = wx.BoxSizer(wx.HORIZONTAL)
        self.topsizer.Add(self.leftpanel, 1, wx.EXPAND)
        self.topsizer.Add(self.rightpanel, 0, wx.EXPAND)
        self.SetSizerAndFit(self.topsizer)
        
        self.ax = self.fig.add_subplot(111)
        self.ax.set_xlabel('Delay (ns)')
        self.ax.set_ylabel('Unnormalised Cross Correlation')
        self.ax.autoscale(tight=True)
        self.canvas.draw()
        
        self.Show()
    
    def CalcCorrelation(self):
        if self.combobox.GetValue() == 'Cross Correlation':
            self.CrossCorrelation()
        elif self.combobox.GetValue() == 'Heralded Cross Correlation':
            self.HeraldedCrossCorrelation()
        elif self.combobox.GetValue() == 'Auto Correlation C0':
            self.autocorrelationchannel = 0
            self.AutoCorrelation()
        elif self.combobox.GetValue() == 'Auto Correlation C1':
            self.autocorrelationchannel = 1
            self.AutoCorrelation()
        else:
            self.autocorrelationchannel = 2
            self.AutoCorrelation()
    
    def OnRunOnce(self,event):
        self.cumulativeflag = False
        self.timetags = self.HRMTime.TimeTags2Mem(self.ncounts,self.recordinglength)
        self.CalcCorrelation()
    
    def OnRunContinuous(self,event):
        if self.DataCollectFlag:
            print 'WARNING: Already collecting data!!!'
        else:
            self.t0 = time.time()
            t = threading.Timer(0, function=self.CalcCorrelationContinuous)
            t.daemon = True
            t.start()
    
    def CalcCorrelationContinuous(self):
        self.DataCollectFlag = True
        self.cumulativeflag = False
        self.timetags = self.HRMTime.TimeTags2Mem(self.ncounts,self.recordinglength)
        self.CalcCorrelation()
        while self.DataCollectFlag:
            self.cumulativeflag = self.cumulativetickbox.GetValue()
            self.timetags = self.HRMTime.TimeTags2Mem(self.ncounts,self.recordinglength)
            self.CalcCorrelation()
    
    def OnStop(self,event):
        self.DataCollectFlag = False
    
    def OnComboSelect(self,event):
        self.OnStop(None)
        self.ax.clear()
        self.canvas.draw()
    
    def OnApply(self,event):
        self.OnStop(None)
        self.recordinglength = int(self.rightpaneltextctrls[0].GetValue())
        self.ncounts = int(self.rightpaneltextctrls[1].GetValue())
        self.dtmax = int(self.rightpaneltextctrls[2].GetValue())
        self.plotbinfactor = int(self.rightpaneltextctrls[3].GetValue())
        self.dntags = int(self.rightpaneltextctrls[4].GetValue())
    
    def OnSaveCorrelation(self,event):
        self.GetFilePath(filetype='.csv',dialoguetype='save')
        try:
            np.savetxt(self.filepath,np.array([self.correlation_x,self.correlation_hist]).transpose(),delimiter=',')
        except:
            np.savetxt(self.filepath,np.array([self.correlation_x, self.cross_correlation_hist, self.heralded_correlation_hist]).transpose(),delimiter=',')
        if self.combobox.GetValue() == 'Cross Correlation':
            header = 'Integration time (s), Ch0 count rate (kHz), Ch1 count rate (kHz)'
            header2 = 'Time from start (s), Integration time (s), Ch0 count rate (kHz), Ch1 count rate (kHz), Ch2 count rate (kHz)'
            np.savetxt(self.filepath[:-4]+'-timed.txt',self.temp_output,header=header2,delimiter=',')
        elif self.combobox.GetValue() == 'Heralded Cross Correlation':
            header = 'Integration time (s), Ch0 count rate (kHz), Ch1 count rate (kHz), Ch2 count rate (kHz)'
            
            np.savetxt(self.filepath[:-4]+'-timed.txt',self.temp_output,header=header2,delimiter=',')
        elif self.combobox.GetValue() == 'Auto Correlation C0':
            header = 'Integration time (s), Ch0 count rate (kHz)'
        elif self.combobox.GetValue() == 'Auto Correlation C1':
            header = 'Integration time (s), Ch1 count rate (kHz)'
        else:
            header = 'Integration time (s), Ch2 count rate (kHz)'
        np.savetxt(self.filepath[:-4]+'-info.txt',self.correlation_info,header=header,delimiter=',')
        # Save g(2) image on screen
        self.fig.savefig(self.filepath[:-4]+'screenshot.png')

    def GetFilePath(self,filetype='.*',dialoguetype='open'):
        if dialoguetype=='open':
            dlg = wx.FileDialog(self, "Choose a file", self.dirname, '', '*'+filetype, wx.OPEN)
        else:
            dlg = wx.FileDialog(self, "Choose a file", self.dirname, '', '*'+filetype, wx.SAVE|wx.OVERWRITE_PROMPT)
        if dlg.ShowModal() == wx.ID_OK:
            self.filename = dlg.GetFilename()
            self.dirname = dlg.GetDirectory()
            self.filepath = os.path.join(self.dirname, self.filename)
        dlg.Destroy()
    
    def CrossCorrelation(self):
        # Store which channel clicks (0, 1 or 2) and the timetag for each click during a [~1 second] period
        channels,times = self.timetags[:,0],self.timetags[:,1] 
        #np.savetxt("debug3/channels.txt", channels)
        #np.savetxt("debug3/timetags.txt", times)
        print "First timetag", times[0] ###
        binsize = 26.9851 
        nbins = int(self.dtmax/binsize + 1e-10) # Expect 1482 bins for dtmax = 40000 ps and binsize 26.9851 picoseconds
        dtmaxact = binsize*nbins
        # histogram resets in cumulative mode
        if self.cumulativeflag == False:
            self.correlation_hist = np.zeros(nbins)
        print '----------------------------------------------------------------'
        for i in range(1,self.dntags+1):
            # Record the index at which there is a click on herald and the "subsequent" click is on signal
            # "Subsequent" is either "the next click" (i.e. i = 1) or "the click after the next" (i.e. i = 2) and so on...
            indices = np.arange(0,len(channels)-i,1,dtype=int)[(channels[:-i] == 0) & (channels[i:] == 1)]
            
            # timegaps are the time between "subsequent" clicks
            timegaps = times[indices+i]-times[indices]
            print "number of timegaps",len(timegaps) ##
            print indices[0:10]
            print str(i)+':', len(timegaps[timegaps<dtmaxact])
            print "dtmaxact", dtmaxact
            # histogram data: x are the bin edges
            hist_i, x = np.histogram(timegaps,bins=nbins,range=(-26.9851/2,dtmaxact-26.9851/2))
            self.correlation_hist += hist_i    
        self.correlation_x = x[:-1]+(x[1]-x[0])/2 # Ensures that leftmost bin starts at t = 0
        # info contains integration time, ch0 count rate, ch1 count rate
        # averages in cumulative mode
        if self.cumulativeflag == False:
            #### Be careful not to have such a low count rate that this no longer gives an accurate integration time
            self.inttime = times[-1]/1e12
            self.ncounts_ch0 = len(channels[channels==0])
            self.ncounts_ch1 = len(channels[channels==1])
            self.ncounts_ch2 = len(channels[channels==2])
            #try:
            #    np.savetxt('delete.csv',np.array([channels,times]).transpose(),delimiter=',')
            #except:
            #    print "couldn't save"

        else:
            #### Be careful not to have such a low count rate that this no longer gives an accurate integration time
            self.inttime += times[-1]/1e12
            self.ncounts_ch0 += len(channels[channels==0])
            self.ncounts_ch1 += len(channels[channels==1])
            self.ncounts_ch2 += len(channels[channels==2])
        print '------------------------------------------'
        print '--  Integration time =', times[-1]/1e12, 's '
        print '--  Ch0 count rate =', len(channels[channels==0])*1e9/times[-1], 'kHz  '
        print '--  Ch1 count rate =', len(channels[channels==1])*1e9/times[-1], 'kHz  '
        print '--  Ch2 count rate =', len(channels[channels==2])*1e9/times[-1], 'kHz  '
        print '------------------------------------------'

        # Record the count rate at each timestep
        self.corr_info = [self.inttime,len(channels[channels==0])*1e9/times[-1],len(channels[channels==1])*1e9/times[-1],len(channels[channels==2])*1e9/times[-1]]
        self.t1 = time.time()
        self.t_elapsed = self.t1 - self.t0
        self.temp_output.append([self.t_elapsed, self.corr_info[0], self.corr_info[1], self.corr_info[2], self.corr_info[3]])
   
        # info contains integration time, ch0 count rate, ch1 count rate
        self.correlation_info = [self.inttime,self.ncounts_ch0*1e-3/self.inttime,self.ncounts_ch1*1e-3/self.inttime,self.ncounts_ch2*1e-3/self.inttime]
        ########## Calculate and print statistics ###########
        # normfactor (Srivathsan 2013)
        normfactor = binsize*1e-12*self.correlation_info[0]*self.correlation_info[1]*1e3*self.correlation_info[2]*1e3
        nbins = len(self.correlation_hist)
        ncor_uncorrected = sum(self.correlation_hist) # Coincidence rate (RSM)
        ncor = sum(self.correlation_hist)-normfactor*nbins # 
        print 'Calculating correlation between Ch0 (herald) and Ch1 (signal)'
        #print 'Calculating unnormalised correlation between Ch1 (herald) and Ch2 (signal)'
        print 'Total Integration time             =', self.correlation_info[0], 's'
        print 'Ch0 average count rate             =', self.correlation_info[1], 'kHz'
        print 'Ch1 average count rate             =', self.correlation_info[2], 'kHz'
        print 'Ch2 average count rate             =', self.correlation_info[3], 'kHz'
        print 'Pair count rate (uncorrected)      =', ncor_uncorrected/self.correlation_info[0], 'Hz'
        print 'Pair count rate (corrected  )      =', ncor/self.correlation_info[0], 'Hz'
        print 'Heralding efficiency (uncorrected) =', ncor_uncorrected/(self.correlation_info[0]*self.correlation_info[1]*1e3)
        print 'Heralding efficiency (corrected  ) =', ncor/(self.correlation_info[0]*self.correlation_info[1]*1e3)
        print ''
        ########### Plot cross correlation vs. time delay #############
        self.ax.clear()
        self.ax.set_xlabel('Delay (ns)')
        self.ax.set_ylabel('Normalised Cross Correlation')
        x,y = bindata(self.correlation_x,self.correlation_hist,self.plotbinfactor)
        self.ax.plot(x/1e3,y/(normfactor*2**self.plotbinfactor))
        self.canvas.draw()        
        
    def AutoCorrelation(self):
        times = self.timetags[self.timetags[:,0]==self.autocorrelationchannel,1]
        binsize = 26.9851
        nbins = int(self.dtmax/binsize + 1e-10)
        dtmaxact = binsize*nbins
        if self.cumulativeflag == False:
            self.correlation_hist = np.zeros(nbins)
        for i in range(1,self.dntags+1):
            timegaps = times[i:]-times[:-i]
            hist_i, x = np.histogram(timegaps,bins=nbins,range=(-26.9851/2,dtmaxact-26.9851/2))
            self.correlation_hist += hist_i
        self.correlation_x = x[:-1]+(x[1]-x[0])/2
        # info contains integration time, count rate of auto correlation channel
        # averages in cumulative mode
        if self.cumulativeflag == False:
            self.inttime = self.timetags[-1,1]*1e-12
            self.ncounts = len(times)
        else:
            self.inttime += self.timetags[-1,1]*1e-12
            self.ncounts += len(times)
        self.correlation_info = [self.inttime,self.ncounts/self.inttime * 1e-3]
        ########### Do Plotting #############
        #try:
        #       print "trying to save..."
        #       np.savetxt('auto1.csv',np.array([times]).transpose(),delimiter=',')
        #       print "saved"
        #except:
        #    print "couldn't save"
        self.ax.clear()
        self.ax.set_xlabel('Delay (ns)')
        self.ax.set_ylabel('Normalised Auto Correlation')
        normfactor = binsize*2**self.plotbinfactor*1e-12*self.correlation_info[0]*(self.correlation_info[1]*1e3)**2
        x,y = bindata(self.correlation_x,self.correlation_hist,self.plotbinfactor)
        self.ax.plot(x/1e3,y/normfactor)
        self.canvas.draw()
        
if __name__ == "__main__":
    app = wx.App(False)
    mainframe = MainFrame(None, "correlator.py")
    app.MainLoop()
