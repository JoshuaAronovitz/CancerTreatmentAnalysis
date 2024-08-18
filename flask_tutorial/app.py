from flask import Flask, request, jsonify, send_file, render_template, render_template_string
import pandas as pd
import plotly.express as px
import plotly.io as pio
import math
import plotly.graph_objects as go

def avg(array):
    sum = 0
    num = len(array)
    for x in array:
        sum += x
    avg = sum/num
    return avg

def std(array, average):
    sum = 0
    for x in array:
        sum += (x - average)*(x - average)
    the_part = sum/(len(array)-1)
    return math.sqrt(the_part)

def percent_error(average, stdev):
    return (stdev/average) * 100

def doublings(final, initial):
    return math.log(final/initial)/math.log(2)
 
def doublings_per_hour(doubling, hour):
    return doubling/hour

def area_under_curve(hours, initial, dph):
    return (initial/(dph*math.log(2)))*(math.exp2(dph*hours)-1)

def final_volume(initialv,initial,final):
    return initialv*final/initial

def mmol_to_mM(initialc, initialv):
    return initialc*initialv/1000

def consumption(initial, final):
    return final - initial

def mmol_per_cell_hour(conPro, auc):
    return conPro/auc

def m_to_f(thing):#millimoles to fentamoles
    return thing*10**12

def lactate_over_glucose(lactate, glucose):
    return math.fabs(lactate/glucose)
 
# def the_combinator(list1, list2, i): #creates a new list
#      if len(list1) != len(list2):
#         return "cannot perform the operation" 
#      else:
#         return [list1[i],list2[i]]  
 
def the_array_treatment_maker(length):
    array = []
    for i in range(1,length+1):
        array.append('treatment ' + str(i))
    return array
 
def the_area_under_curve_array(length, df): #makes calculations easier
    array = []
    array2 = []
    for i in range(1,length + 1):
       array2 = df['treatment ' + str(i) + ' AUC'].tolist()
       d = doublings(array2[2], array2[1])
       dph = doublings_per_hour(d, array2[0])
       auc = area_under_curve(array2[0], array2[1], dph)
       array.append(auc)
    return array

def the_y_values_array(length, df, area_array, initial_volume, final_volume, chemical):
    array = []
    array2 = []
    array3 = []
    for i in range(1, length+1):
        array2 = df["treatment " + str(i) + " initial concentration " + chemical].tolist()
        array3 = df["treatment " + str(i) + " final concentration " + chemical].tolist()
        for j in range(0,len(array2)):
            array2[j] = array2[j] * initial_volume / 1000
            array3[j] = array3[j] * final_volume / 1000
            array2[j] = -1 * consumption(array2[j], array3[j])
            array2[j] = m_to_f(array2[j])
            array2[j] = mmol_per_cell_hour(array2[j], area_array[i-1])
        arr_avg = avg(array2)
        array.append(arr_avg)
    return array

def the_stdev_array(length, df, area_array, initial_volume, final_volume, chemical):
    array = []
    array2 = []
    array3 = []
    for i in range(1, length+1):
        array2 = df['treatment ' + str(i) + ' initial concentration ' + chemical].tolist()
        array3 = df['treatment ' + str(i) + ' final concentration ' + chemical].tolist()
        for j in range(0,len(array2)):
            array2[j] = mmol_to_mM(array2[j], initial_volume)
            array3[j] = mmol_to_mM(array3[j], final_volume)
            array2[j] = consumption(array2[j], array3[j])
            array2[j] = m_to_f(array2[j])
            array2[j] = mmol_per_cell_hour(array2[j], area_array[i - 1])
        arr_avg = avg(array2)
        arr_std = std(array2, arr_avg)
        array.append(arr_std)
    return array
             
app = Flask(__name__)

@app.route("/")
def index():
    return '''<!doctype html>
<title>Upload a File, Recieve a Graph</title>
<h1>Choose Your File</h1>
<form method = "post" enctype = "multipart/form-data" action = "/upload">
    <input type = "file" name="file">
    <label for = "textbox">Enter what chemical you want to analyze:</label>
    <input type = "text" id = "textbox" name = "textbox">
    <label for "textbox"> How many treatments are there?:</label>
    <input type = "text" id = "textbox2" name = "textbox2">
    <input type = "submit" value = "Upload">
</form>'''
    # return render_template("web.html")


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'No file part'
    file = request.files['file']
    
    if file.filename == '':
        return 'No selected file'
    
    if not file.filename.endswith('.xlsx'):
        return 'invalid file format'
    
    chemical = request.form.get('textbox', '')#this will be used to determine what graph we want
    length = request.form.get('textbox2', '')
    df = pd.read_excel(file) #after this I shall create a graph
    intitial_volume_arr = df['initial volume'].tolist() #get the initial volume array
    initial_volume = intitial_volume_arr[0]#get the initial volume
    #we are going to assume that their are only 3 treatments
    control_initial = df['initial concentration no cells'].tolist()
    control_final = df['final concentration no cells'].tolist()
    control_initial_avg = avg(control_initial)
    control_final_avg = avg(control_final)
    final_volume = initial_volume * control_final_avg / control_initial_avg #we now have the initial
    #volume and the final volume. This is necessary for converting the units
    x_values = the_array_treatment_maker(int(length))#the value scanned is a string
    area_array = the_area_under_curve_array(int(length), df)
    y_values = the_y_values_array(int(length), df, area_array, initial_volume, final_volume, chemical)
    the_errors = the_stdev_array(int(length), df, area_array, initial_volume, final_volume, chemical)
    fig = go.Figure(data = go.Bar( 
        x= x_values, 
        y= y_values, 
        error_y = dict(
              # value of error bar given in data coordinates 
            type ='data', 
            array = the_errors, 
            visible = True))) 
    fig.update_layout(
    title= chemical,
    xaxis_title="Treatments",
    yaxis_title="fMols/(cell*hour)",
    font=dict(
        family="Courier New, monospace",
        size=18,
        color="RebeccaPurple"
    )
) 
    graph_html = pio.to_html(fig,full_html=False)
    
    return render_template_string(''' 
    <!doctype html>
    <title>Plot</title>
    <h1>Plot</h1>
    <div>{{graph_html | safe}}</div>
    <a href="/"> Upload another file </a>''', graph_html = graph_html)

if __name__ == '__main__':
    app.run(debug=True)