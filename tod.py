import sqlite3
import os
import numpy as np
from time import sleep, time
from math import ceil
from multiprocessing import Process, shared_memory
from pathlib import Path
from sklearn.cluster import KMeans
from sklearn.datasets import make_blobs
import xml.etree.ElementTree as ET
import traci

ROOT = Path.cwd()
DIR_SUMO = ROOT / 'IKSAN'
DIR_SUMO_NET = DIR_SUMO / 'net'
DIR_SUMO_ROU = DIR_SUMO / 'rou'
DIR_SUMO_CFG = DIR_SUMO / 'cfg'
DIR_DB = ROOT / 'db'
tree_netinfo = ET.parse(DIR_SUMO_NET / 'IKSAN.net.xml')
root_netinfo = tree_netinfo.getroot()

class TodInputModule:
    
    def __init__(self, number, tlLogic_name, k_0, k_1, k_2, k_cen):
        
        self.number = number
        self.tlLogic_name = tlLogic_name
        self.k_0 = k_0
        self.k_1 = k_1
        self.k_2 = k_2
        self.k_cen = k_cen
               
    def create_tod_table(self):
        before = time()
        
        
        # PROCESS_NUM = 4
        PROCESS_NUM = 8
        
        conn = sqlite3.connect(DIR_DB / "test.db", isolation_level=None)
        cur = conn.cursor()
        cur.execute("SELECT from_,volume,time FROM table1")
        table = cur.fetchall()

        cur.execute("SELECT volume, from_, to_, direct, time FROM table2")
        table_ = cur.fetchall()
        from_=[]
        to_=[]
        dead_end = []
        
        for l in range(0, len(table_)):
            from_.append(table_[l][1])
            to_.append(table_[l][2])
        for s in range(len(set(to_))):
            sto_ = list(set(to_))
            if sto_[s] not in from_:
                dead_end.append(sto_[s])    
        sink = " ".join(dead_end)
        
        tv_ = []
        table_volume = []
        cur.execute("SELECT volume from table2")
        tv = cur.fetchall()
        for t in range(len(tv)):
            tv_ += tv[t]
        table_volume = self.chunk_list(tv_, 12)

        cur.close()
        conn.commit()
        conn.close()

        X = np.array(table_volume)

        k_means = KMeans(init="k-means++", n_clusters=3, n_init=15)
        k_means.fit(X)

        k_means_labels = k_means.labels_
        k_means_cluster_centers = k_means.cluster_centers_
        k = k_means_cluster_centers

        shl = shared_memory.ShareableList(range(40))
        
        chunk_phase_list = []
        self.chunk_phase_list_(chunk_phase_list, self.number, self.tlLogic_name, PROCESS_NUM)
                
        tree_netinfo = ET.parse(DIR_SUMO_NET / 'IKSAN.net.xml')
        root_netinfo = tree_netinfo.getroot()

        edge_id = []
        edge_from = []
        junction_id = []
        junction_type = []
        lane_length = []
        lane_idlist = []
        length = []
        con_from_ = []
        con_to_ = []

        for net in root_netinfo.iter('edge'):
            edge_id.append(net.get('id'))
            edge_from.append(net.get('from'))

        for jun in tree_netinfo.iter('junction'):
            junction_id.append(jun.get('id'))
            junction_type.append(jun.get('type'))
            
        for con in tree_netinfo.iter('connection'):
            con_from_.append(con.get('from'))
            con_to_.append(con.get('to')) 
            
        for i in range(4):
            for lane in tree_netinfo.iter('lane'):
                lane_length.append(lane.get('length'))
                lane_idlist.append(lane.get('id'))
                lane_id = lane.get('id')  
                if lane_id.split("_")[0] == table[i][0]:
                    length.append(lane_length[lane_idlist.index(lane_id)])
                    
                 
        traffic = []
        phase = []
        phasein = []
        tod_ = []
        
        for cen in range(3):
            self.generate_flowfile(cen, table, k, edge_id, edge_from, junction_id, junction_type, con_from_, con_to_, length)
            self.generate_turnfile(cen, table_, sink, k)
            
            os.system('jtrrouter -n ./IKSAN/net/IKSAN.net.xml \
                -r ./IKSAN/rou/clus.flow.xml \
                -t ./IKSAN/rou/clus.turn.xml \
                -o ./IKSAN/rou/clus.rou.xml --randomize-flows')
            
            nm = self.normal_tod_waitingtime(table, cen, k, self.number)
            
            shm_name = shl.shm.name
            
            p1 = Process(target=self.run_simulation, args=([chunk_phase_list[0], 1, shm_name, nm, table, cen, k, self.number, self.tlLogic_name]))
            p2 = Process(target=self.run_simulation, args=([chunk_phase_list[1], 2, shm_name, nm, table, cen, k, self.number, self.tlLogic_name]))
            p3 = Process(target=self.run_simulation, args=([chunk_phase_list[2], 3, shm_name, nm, table, cen, k, self.number, self.tlLogic_name]))
            p4 = Process(target=self.run_simulation, args=([chunk_phase_list[3], 4, shm_name, nm, table, cen, k, self.number, self.tlLogic_name]))
            p5 = Process(target=self.run_simulation, args=([chunk_phase_list[4], 5, shm_name, nm, table, cen, k, self.number, self.tlLogic_name]))
            p6 = Process(target=self.run_simulation, args=([chunk_phase_list[5], 6, shm_name, nm, table, cen, k, self.number, self.tlLogic_name]))
            p7 = Process(target=self.run_simulation, args=([chunk_phase_list[6], 7, shm_name, nm, table, cen, k, self.number, self.tlLogic_name]))
            p8 = Process(target=self.run_simulation, args=([chunk_phase_list[7], 8, shm_name, nm, table, cen, k, self.number, self.tlLogic_name]))
            
            p1.start()
            p2.start()
            p3.start()
            p4.start()
            p5.start()
            p6.start()
            p7.start()
            p8.start()
            
            p1.join()
            p2.join()
            p3.join()
            p4.join()
            p5.join()
            p6.join()
            p7.join()
            p8.join()
            
            print(shl)
            
            if shl[4] > shl[9] and shl[4] > shl[14] and shl[4] > shl[19] and shl[4] > shl[24] and shl[4] > shl[29] and shl[4] > shl[34] and shl[4] > shl[39]:
                print(f"pahse : {shl[0],shl[1],shl[2],shl[3]} Improvement : {shl[4]} %")
                traffic.append([f"pahse : {[shl[0],shl[1],shl[2],shl[3]]} Improvement : {shl[4]} %"])
                phase.append(f"{shl[0]}, {shl[1]}, {shl[2]}, {shl[3]}")
                phasein.append([shl[0], shl[1], shl[2], shl[3]])
            elif shl[9] > shl[4] and shl[9] > shl[14] and shl[9] > shl[19] and shl[9] > shl[24] and shl[9] > shl[29] and shl[9] > shl[34] and shl[9] > shl[39]:
                print(f"phase : {shl[5],shl[6],shl[7],shl[8]} Improvement : {shl[9]} %")
                traffic.append([f"phase : {[shl[5],shl[6],shl[7],shl[8]]} Improvement : {shl[9]} %"])
                phase.append(f"{shl[5]}, {shl[6]}, {shl[7]}, {shl[8]}")
                phasein.append([shl[5], shl[6], shl[7], shl[8]])
            elif shl[14] > shl[4] and shl[14] > shl[9] and shl[14] > shl[19] and shl[14] > shl[24] and shl[14] > shl[29] and shl[14] > shl[34] and shl[14] > shl[39]:
                print(f"phase : {shl[10],shl[11],shl[12],shl[13]} Improvement : {shl[14]} %")
                traffic.append([f"phase : {[shl[10],shl[11],shl[12],shl[13]]} Improvement : {shl[14]} %"])
                phase.append(f"{shl[10]}, {shl[11]}, {shl[12]}, {shl[13]}")
                phasein.append([shl[10], shl[11], shl[12], shl[13]])
            elif shl[19] > shl[4] and shl[19] > shl[9] and shl[19] > shl[14] and shl[19] > shl[24] and shl[19] > shl[29] and shl[19] > shl[34] and shl[14] > shl[39]:
                print(f"phase : {shl[15],shl[16],shl[17],shl[18]}] Improvement : {shl[19]} %")
                traffic.append([f"phase : {[shl[15],shl[16],shl[17],shl[18]]} Improvement : {shl[19]} %"])
                phase.append(f"{shl[15]}, {shl[16]}, {shl[17]}, {shl[18]}")
                phasein.append([shl[15], shl[16], shl[17], shl[18]])
            elif shl[24] > shl[29] and shl[24] > shl[34] and shl[24] > shl[39] and shl [24] > shl[4] and shl [24] > shl[9] and shl [24] > shl[14] and shl [24] > shl[19]:
                print(f"pahse : {shl[20],shl[21],shl[22],shl[23]} Improvement : {shl[24]} %")
                traffic.append([f"pahse : {[shl[20],shl[21],shl[22],shl[23]]} Improvement : {shl[24]} %"])
                phase.append(f"{shl[20]}, {shl[21]}, {shl[22]}, {shl[23]}")
                phasein.append([shl[20], shl[21], shl[22], shl[23]])
            elif shl[29] > shl[24] and shl[29] > shl[34] and shl[29] > shl[39] and shl [29] > shl[4] and shl [29] > shl[9] and shl [29] > shl[14] and shl [29] > shl[19]:
                print(f"phase : {shl[25],shl[26],shl[27],shl[28]} Improvement : {shl[29]} %")
                traffic.append([f"phase : {[shl[25],shl[26],shl[27],shl[28]]} Improvement : {shl[29]} %"])
                phase.append(f"{shl[25]}, {shl[26]}, {shl[27]}, {shl[28]}")
                phasein.append([shl[25], shl[26], shl[27], shl[28]])
            elif shl[34] > shl[24] and shl[34] > shl[29] and shl[34] > shl[39] and shl [34] > shl[4] and shl [34] > shl[9] and shl [34] > shl[14] and shl [34] > shl[19]:
                print(f"phase : {shl[30],shl[31],shl[32],shl[33]} Improvement : {shl[34]} %")
                traffic.append([f"phase : {[shl[30],shl[31],shl[32],shl[33]]} Improvement : {shl[34]} %"])
                phase.append(f"{shl[30]}, {shl[31]}, {shl[32]}, {shl[33]}")
                phasein.append([shl[30], shl[31], shl[32], shl[33]])
            elif shl[39] > shl[24] and shl[39] > shl[29] and shl[39] > shl[34] and shl [39] > shl[4] and shl [39] > shl[9] and shl [39] > shl[14] and shl [39] > shl[19]:
                print(f"phase : {shl[35],shl[36],shl[37],shl[38]}] Improvement : {shl[39]} %")
                traffic.append([f"phase : {[shl[35],shl[36],shl[37],shl[38]]} Improvement : {shl[39]} %"])
                phase.append(f"{shl[35]}, {shl[36]}, {shl[37]}, {shl[38]}")
                phasein.append([shl[35], shl[36], shl[37], shl[38]])
            
        print(f"traffic 1 : {traffic[0]} traffic 2 : {traffic[1]} traffic 3 : {traffic[2]}")
        shl.shm.close()
        shl.shm.unlink()
        for cen in range(3):
            for sert in range(len(list(filter(lambda x : k_means_labels[x] == cen, range(len(k_means_labels)))))):
                tod_.insert((list(filter(lambda x : k_means_labels[x] == cen, range(len(k_means_labels)))))[sert], [(list(filter(lambda x : k_means_labels[x] == cen, range(len(k_means_labels)))))[sert], phase[cen]])
            print(list(filter(lambda x : k_means_labels[x] == cen, range(len(k_means_labels)))), cen)
            print(k[cen].round(0))
        conn = sqlite3.connect(DIR_DB / "tod_table.db")
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS tod_table \
            (time_slot integer PRIMARY KEY, phase text)")
        conn.execute("DELETE FROM tod_table")
        c.executemany("INSERT INTO tod_table(time_slot, phase) VALUES(?,?)", tod_)
        
        with conn:
            with open(DIR_DB / 'dump_tod.sql', 'w') as f:
                for line in conn.iterdump():
                    f.write('%s/n' % line)
                print('Completed.')
        after = time()
        x = after - before
        print(f"time : {x / 60}min")
        hour_list = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]
        si_tod_table = []
        
        for a in range(320):
            si_tod_table.append(0)
            
        s_index = 0
            
        for s in hour_list:
            if s == 0:
                si_tod_table[s] = s
                si_tod_table[2] = sum(phasein[k_means_labels[s]])
                si_tod_table[4] = phasein[k_means_labels[s]][0]
                si_tod_table[6] = phasein[k_means_labels[s]][1]
                si_tod_table[8] = phasein[k_means_labels[s]][2]
                si_tod_table[10] = phasein[k_means_labels[s]][3]
                
                s_index += 20

            elif s != 0 and k_means_labels[s] != k_means_labels[s-1]:
                si_tod_table[s_index] = s
                si_tod_table[2 + s_index] = sum(phasein[k_means_labels[s]])
                si_tod_table[4 + s_index] = phasein[k_means_labels[s]][0]
                si_tod_table[6 + s_index] = phasein[k_means_labels[s]][1]
                si_tod_table[8 + s_index] = phasein[k_means_labels[s]][2]
                si_tod_table[10 + s_index] = phasein[k_means_labels[s]][3]
                
                s_index += 20
                
            elif s != 0 and k_means_labels[s] == k_means_labels[s-1]:
                continue
          
        return si_tod_table
        
    def chunk_list(self, lst, size):
        return list(map(lambda x: lst[x * size:x * size + size],list(range(ceil(len(lst) / size)))))
    
    def split_phase_3(self, cycle, min_green:list):
        phase_list = []
        i = []
        
        remain_cycle = cycle - 12 -sum(min_green)
        if remain_cycle % 4 == 0:
            denominator = 4
        elif remain_cycle % 3 == 0:
            denominator = 3
        elif remain_cycle % 2 == 0:
            denominator = 2
        elif remain_cycle % 5 == 0:
            denominator = 5
        else: 
            remain_cycle = cycle - 12 - sum(min_green) - 1
            if remain_cycle % 4 == 0:
                denominator = 4
                min_green[min_green.index(max(min_green))] = min_green[min_green.index(max(min_green))] + 1

            else:
                remain_cycle = cycle - 12 - sum(min_green) + 1
                denominator = 4  
                min_green[min_green.index(max(min_green))] = min_green[min_green.index(max(min_green))] - 1
        
        for x in range(int(remain_cycle / denominator) + 1):
            y = x * denominator
            i.append(y)
        

        for m in i:
            for n in i:
                for o in i:
                        if m + n + o == remain_cycle:
                            
                            a = min_green[0] + 4 + m
                            b = min_green[1] + 4 + n
                            c = min_green[2] + 4 + o
                            
                            phase_list.append([a, b, c])
                        else:
                            continue
                    
        return phase_list
    
    def split_phase_4(self, cycle, min_green:list):
    
        phase_list = []
        i = []
        
        remain_cycle = cycle - 16 - sum(min_green)
        if remain_cycle % 4 == 0:
            denominator = 4
        elif (remain_cycle - 1) % 4 == 0:
            remain_cycle = cycle -16 - sum(min_green) - 1
            denominator = 4
            min_green[min_green.index(max(min_green))] = min_green[min_green.index(max(min_green))] + 1
        elif (remain_cycle + 1) % 4 == 0:
            remain_cycle = cycle - 16 - sum(min_green) + 1
            denominator = 4 
            min_green[min_green.index(max(min_green))] = min_green[min_green.index(max(min_green))] - 1
        elif remain_cycle % 3 == 0:
            denominator = 3
        elif remain_cycle % 5 == 0:
            denominator = 5
        elif remain_cycle % 2 == 0: 
            denominator = 2 
        
        for x in range(int(remain_cycle / denominator) + 1):
            y = x * denominator
            i.append(y)
        
        for m in i:
            for n in i:
                for o in i:
                    for p in i:
                        if m + n + o + p == remain_cycle:
                            
                            a = min_green[0] + 4 + m
                            b = min_green[1] + 4 + n
                            c = min_green[2] + 4 + o
                            d = min_green[3] + 4 + p
                            
                            phase_list.append([a, b, c, d])
                        else:
                            continue
        return phase_list
    
    def split_phase_5(self, cycle, min_green:list):
    
        phase_list = []
        i = []
        
        remain_cycle = cycle - 20 - sum(min_green)
        if remain_cycle % 5 == 0:
            denominator = 5
        elif remain_cycle % 4 == 0:
            denominator = 4
        elif (remain_cycle - 1) % 4 == 0:
            remain_cycle = cycle - 20 - sum(min_green) - 1
            denominator = 4
            min_green[min_green.index(max(min_green))] = min_green[min_green.index(max(min_green))] + 1
        elif (remain_cycle + 1) % 4 == 0:
            remain_cycle = cycle - 20 - sum(min_green) + 1
            denominator = 4 
            min_green[min_green.index(max(min_green))] = min_green[min_green.index(max(min_green))] - 1
        elif remain_cycle % 3 == 0:
            denominator = 3
        elif remain_cycle % 2 == 0: 
            denominator = 2

        for x in range(int(remain_cycle / denominator) + 1):
            y = x * denominator
            i.append(y)
        
        for m in i:
            for n in i:
                for o in i:
                    for p in i:
                        for q in i:
                            if m + n + o + p + q == remain_cycle:
                                
                                a = min_green[0] + 4 + m
                                b = min_green[1] + 4 + n
                                c = min_green[2] + 4 + o
                                d = min_green[3] + 4 + p
                                e = min_green[4] + 4 + q                        
                                phase_list.append([a, b, c, d, e])
                            else:
                                continue
                    
        return phase_list
      
    def chunk_phase_list_(self, chunk_phase_list:list, number, tlLogic_name, PROCESS_NUM):
        for n in range(number):
            if n == 0:
                if '1.Sindong396-7' == tlLogic_name[0]:
                    for ch in range(8):
                        chunk_phase_list.append([self.chunk_list(self.split_phase_4(160, [28, 32, 28, 32]), ceil(len(self.split_phase_4(160, [28, 32, 28, 32])) / PROCESS_NUM))[ch]])
                
                elif '2.sindong830' == tlLogic_name[0]:
                    for ch in range(8):
                        chunk_phase_list.append([self.chunk_list(self.split_phase_4(160, [32, 15, 31, 30]), ceil(len(self.split_phase_4(160, [32, 15, 31, 30])) / PROCESS_NUM))[ch]])
                
                elif '3.sindong120-23' == tlLogic_name[0]:
                    for ch in range(8):
                        chunk_phase_list.append([self.chunk_list(self.split_phase_4(160, [15, 26, 26, 26]), ceil(len(self.split_phase_4(160, [15, 26, 26, 26])) / PROCESS_NUM))[ch]])
                
                elif '4.yeongdengdong870' == tlLogic_name[0]:
                    for ch in range(8):
                        chunk_phase_list.append([self.chunk_list(self.split_phase_4(160, [24, 24, 29, 25]), ceil(len(self.split_phase_4(160, [24, 24, 29, 25])) / PROCESS_NUM))[ch]])
                
                elif '5.yeongdengdong870-1' == tlLogic_name[0]:
                    for ch in range(8):
                        chunk_phase_list.append([self.chunk_list(self.split_phase_5(160, [35, 15, 26, 26, 15]), ceil(len(self.split_phase_5(160, [35, 15, 26, 26, 15])) / PROCESS_NUM))[ch]])
                
                elif '6.eoyangdong663' == tlLogic_name[0]:
                    for ch in range(8):
                        chunk_phase_list.append([self.chunk_list(self.split_phase_4(160, [15, 40, 28, 28]), ceil(len(self.split_phase_4(160, [15, 40, 28, 28])) / PROCESS_NUM))[ch]])
                
                elif '7.busongdong1060' == tlLogic_name[0]:
                    for ch in range(8):
                        chunk_phase_list.append([self.chunk_list(self.split_phase_4(160, [38, 15, 27, 27]), ceil(len(self.split_phase_4(160, [38, 15, 27, 27])) / PROCESS_NUM))[ch]])
                        
                elif '8.busongdongsan266-4' == tlLogic_name[0]:
                    for ch in range(8):
                        chunk_phase_list.append([self.chunk_list(self.split_phase_5(160, [15, 32, 15, 24, 25]), ceil(len(self.split_phase_5(160, [15, 32, 15, 24, 25])) / PROCESS_NUM))[ch]])
                
                elif '9.busongdong224-8' == tlLogic_name[0]:
                    for ch in range(8):
                        chunk_phase_list.append([self.chunk_list(self.split_phase_5(160, [30, 30, 9, 15, 15]), ceil(len(self.split_phase_5(160, [30, 30, 9, 15, 15])) / PROCESS_NUM))[ch]])
                
                elif '10. IKSANfirestation' == tlLogic_name[0]:
                    for ch in range(8):
                        chunk_phase_list.append([self.chunk_list(self.split_phase_3(90, [24, 6, 6]), ceil(len(self.split_phase_3(90, [24, 6, 6])) / PROCESS_NUM))[ch]])
            
            elif n > 0:
                if tlLogic_name[n] == '1.Sindong396-7':
                    for ca in range(8):
                        chunk_phase_list[ca].append(self.chunk_list(self.split_phase_4(160, [28, 32, 28, 32]), ceil(len(self.split_phase_4(160, [28, 32, 28, 32])) / PROCESS_NUM))[ca])
                
                elif tlLogic_name[n] == '2.sindong830':
                    for ca in range(8):
                        chunk_phase_list[ca].append(self.chunk_list(self.split_phase_4(160, [32, 15, 31, 30]), ceil(len(self.split_phase_4(160, [32, 15, 31, 30])) / PROCESS_NUM))[ca])
                        
                elif tlLogic_name[n] == '3.sindong120-23':
                    for ca in range(8):
                        chunk_phase_list[ca].append(self.chunk_list(self.split_phase_4(160, [15, 26, 26, 26]), ceil(len(self.split_phase_4(160, [15, 26, 26, 26])) / PROCESS_NUM))[ca])
                        
                elif tlLogic_name[n] == '4.yeongdengdong870':
                    for ca in range(8):
                        chunk_phase_list[ca].append(self.chunk_list(self.split_phase_4(160, [24, 24, 29, 25]), ceil(len(self.split_phase_4(160, [24, 24, 29, 25])) / PROCESS_NUM))[ca])
                        
                elif tlLogic_name[n] == '5.yeongdengdong870-1':
                    for ca in range(8):
                        chunk_phase_list[ca].append(self.chunk_list(self.split_phase_5(160, [35, 15, 26, 26, 15]), ceil(len(self.split_phase_5(160, [35, 15, 26, 26, 15])) / PROCESS_NUM))[ca])
                        
                elif tlLogic_name[n] == '6.eoyangdong663':
                    for ca in range(8):
                        chunk_phase_list[ca].append(self.chunk_list(self.split_phase_4(160, [15, 40, 28, 28]), ceil(len(self.split_phase_4(160, [15, 40, 28, 28])) / PROCESS_NUM))[ca])
                
                elif tlLogic_name[n] == '7.busongdong1060':
                    for ca in range(8):
                        chunk_phase_list[ca].append(self.chunk_list(self.split_phase_4(160, [38, 15, 27, 27]), ceil(len(self.split_phase_4(160, [38, 15, 27, 27])) / PROCESS_NUM))[ca])
                                
                elif tlLogic_name[n] == '8.busongdongsan266-4':
                    for ca in range(8):
                        chunk_phase_list[ca].append(self.chunk_list(self.split_phase_5(160, [15, 32, 15, 24, 25]), ceil(len(self.split_phase_5(160, [15, 32, 15, 24, 25])) / PROCESS_NUM))[ca])
                        
                elif tlLogic_name[n] == '9.busongdong224-8':
                    for ca in range(8):
                        chunk_phase_list[ca].append(self.chunk_list(self.split_phase_5(160, [30, 30, 9, 15, 15]), ceil(len(self.split_phase_5(160, [30, 30, 9, 15, 15])) / PROCESS_NUM))[ca])
                                           
                elif tlLogic_name[n] == '10.IKSANfirestation':
                    for ca in range(8):
                        chunk_phase_list[ca].append(self.chunk_list(self.split_phase_3(90, [24, 6 , 6]), ceil(len(self.split_phase_3(90, [24, 6 , 6])) / PROCESS_NUM))[ca])

        return chunk_phase_list
    
    def generate_flowfile(self, cen, table, k, edge_id, edge_from, junction_id, junction_type, con_from_, con_to_, length):
        k_means_cluster_centers = k
        for a, b, c, d in zip(range(3), range(3, 6), range(6, 9), range(9, 12)):
            if cen == 0:
                
                self.k_0[0] += k_means_cluster_centers[cen].round(0)[a]
                self.k_0[1] += k_means_cluster_centers[cen].round(0)[b]
                self.k_0[2] += k_means_cluster_centers[cen].round(0)[c]
                self.k_0[3] += k_means_cluster_centers[cen].round(0)[d]
            elif cen == 1:
                
                self.k_1[0] += k_means_cluster_centers[cen].round(0)[a]
                self.k_1[1] += k_means_cluster_centers[cen].round(0)[b]
                self.k_1[2] += k_means_cluster_centers[cen].round(0)[c]
                self.k_1[3] += k_means_cluster_centers[cen].round(0)[d]
            elif cen == 2:

                self.k_2[0] += k_means_cluster_centers[cen].round(0)[a]
                self.k_2[1] += k_means_cluster_centers[cen].round(0)[b]
                self.k_2[2] += k_means_cluster_centers[cen].round(0)[c]
                self.k_2[3] += k_means_cluster_centers[cen].round(0)[d]        
        
        with open(DIR_SUMO_ROU / "clus.flow.xml", "w") as flow:
            print("""<routes>""", file = flow)       
            for i in range(4):             
                if junction_type[junction_id.index(edge_from[edge_id.index(table[i][0])])] == ("dead_end") and float(list(dict.fromkeys(length))[i]) < 100:
                    print("""    <flow id="%s_%d" from="%s" departlane="best" departPos="base" begin="%d" end="%d" number="%d"/>""" \
                    % (table[i][0], cen, table[i][0], 0, 3600, self.k_cen[cen][i]), file = flow)
                elif junction_type[junction_id.index(edge_from[edge_id.index(table[i][0])])] == ("dead_end") and float(list(dict.fromkeys(length))[i]) >= 100:
                    print("""    <flow id="%s_%d" from="%s" departlane="best" departPos="%d" begin="%d" end="%d" number="%d"/>""" \
                    % (table[i][0], cen, table[i][0], float(list(dict.fromkeys(length))[i]) - 100, 0, 3600, self.k_cen[cen][i]), file = flow)    
                elif junction_type[junction_id.index(edge_from[edge_id.index(table[i][0])])] != ("dead_end") and float(list(dict.fromkeys(length))[i]) >= 100:
                    print("""    <flow id="%s_%d" from="%s" departlane="best" departPos="%d" begin="%d" end="%d" number="%d"/>""" \
                    % (table[i][0], cen, table[i][0], float(list(dict.fromkeys(length))[i]) - 100, 0, 3600, self.k_cen[cen][i]), file = flow)
                elif junction_type[junction_id.index(edge_from[edge_id.index(table[i][0])])] != ("dead_end") and float(list(dict.fromkeys(length))[i]) < 100:
                    print("""    <flow id="%s_%d" from="%s" departlane="best" departPos="base" begin="%d" end="%d" number="%d"/>""" \
                        % (table[i][0], cen, con_from_[con_to_.index(table[i][0])], 0, 3600, self.k_cen[cen][i]), file = flow)
            print("""</routes>""", file = flow)

    def generate_turnfile(self, cen, table_, sink, k):
        k_means_cluster_centers = k
        with open(DIR_SUMO_ROU / "clus.turn.xml", "w") as turn:
                print("""<edgeRelations>""", file = turn)
                print("""    <interval begin="%s" end="%s"> """ % (0, 3600), file = turn)
                for tn in range(0, len(k_means_cluster_centers[cen])):
                    if tn in range(3):
                        i = 0
                    if tn in range(3, 6):
                        i = 1
                    if tn in range(6, 9):
                        i = 2
                    if tn in range(9, 12):
                        i = 3
                    try:    
                        print("""    <edgeRelation from="%s" to="%s" probability="%s"/>""" % (table_[tn][1], table_[tn][2], \
                        round(k_means_cluster_centers[cen].round(0)[tn]/self.k_cen[cen][i], 2)), file = turn)
                    except ZeroDivisionError:
                        print("""    <edgeRelation from="%s" to="%s" probability="%s"/>""" % (table_[tn][1], table_[tn][2], 0), file = turn)
                print(f"""    </interval>
        <sink edges="{sink}"/>""", file = turn)
                print("""</edgeRelations>
                            """, file = turn)
                
    def generate_cfgfile(self, idx):
        
        with open(DIR_SUMO_CFG / f"its{idx}.sumocfg", "w") as cfg :
            print("""<?xml version="1.0" encoding="UTF-8"?>""", file = cfg)
            print("""<configuration xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dir.de/xsd/sumoConfiguration.xsd">""", file = cfg)
            print("""    <input>""", file = cfg)
            print(f"""        <net-file value="../net/IKSAN.net.xml"/>
        <route-files value="../rou/clus.rou.xml"/>
        <additional-files value="../add/its{idx}.xml"/>""", file = cfg)
            print("""    </input>""", file = cfg)
        
            print("""    <gui_only>
        <registry-viewport value="true"/>""", file = cfg)
            print("""    </gui_only>""", file = cfg)
            print("""</configuration>""" , file = cfg)
       
    def generate_addfile(self, idx, table, number, tlLogic_name, phases, phase_list):
        
        tree_netinfo = ET.parse(DIR_SUMO_NET / "IKSAN.net.xml")
        root_netinfo = tree_netinfo.getroot() 
        tl_list = []        
        for tl in root_netinfo.iter('tlLogic'):
            
            if number == 1:   
                if tl.attrib.get('id') == '%s' % tlLogic_name[0]:            
                    with open(f"./IKSAN/add/its{idx}.xml", "w") as tlLogic:
                        print("""<additional>""", file = tlLogic)
                        if len(tl) <= 10:                
                            print(f"""    <{tl.tag} id="{tl.attrib.get('id')}" type="{tl.attrib.get('type')}" programID="{", ".join(str(s) for s in phases)}" offset="{tl.attrib.get('offset')}">""", file = tlLogic)
                        else:
                            continue
                        for n in range(len(tl)):
                            if n % 2 == 0:
                                d = phases[int(n / 2)] - 4
                            elif n % 2 != 0:
                                d = 4
                            print(f"""        <{tl[0].tag} duration="{d}" state="{tl[n].attrib.get('state')}"/>""", file = tlLogic) 
                    with open(f"./IKSAN/add/its{idx}.xml", "a") as tlLogic:
                        print(f"""    </{tl.tag}>""", file = tlLogic)
                        print("""</additional>""", file = tlLogic)
            elif number > 1:
                for nint in range(number):     
                    if nint == 0 and tl.attrib.get('id') == '%s' % tlLogic_name[0]:
                        with open(f"./IKSAN/add/its{idx}.xml", "w") as tlLogic:
                            print("""<additional>""", file = tlLogic) 
                            try:
                                print(f"""    <{tl.tag} id="{tl.attrib.get('id')}" type="{tl.attrib.get('type')}" programID="{", ".join(str(s) for s in phase_list[nint][phases])}" offset="{tl.attrib.get('offset')}">""", file = tlLogic)
                            except IndexError:
                                continue
                            for n in range(len(tl)):
                                if n % 2 == 0:
                                    d = phase_list[nint][phases][int(n / 2)] - 4
                                elif n % 2 != 0:
                                    d = 4
                                print(f"""        <{tl[0].tag} duration="{d}" state="{tl[n].attrib.get('state')}"/>""", file = tlLogic)
                            print(f"""    </{tl.tag}>""", file = tlLogic)
                    elif nint != 0 and nint != number - 1 and tl.attrib.get('id') == '%s' % tlLogic_name[nint]:      
                        if tl.attrib.get('id') not in tl_list:
                            with open(f"./IKSAN/add/its{idx}.xml", "a") as tlLogic:
                                try:
                                    print(f"""    <{tl.tag} id="{tl.attrib.get('id')}" type="{tl.attrib.get('type')}" programID="{", ".join(str(s) for s in phase_list[nint][phases])}" offset="{tl.attrib.get('offset')}">""", file = tlLogic)
                                except IndexError:
                                    continue
                                for n in range(len(tl)):
                                    if n % 2 == 0:
                                        d = phase_list[nint][phases][int(n / 2)] - 4
                                    elif n % 2 != 0:
                                        d = 4
                                    print(f"""        <{tl[0].tag} duration="{d}" state="{tl[n].attrib.get('state')}"/>""", file = tlLogic)
                            with open(f"./IKSAN/add/its{idx}.xml", "a") as tlLogic:
                                print(f"""    </{tl.tag}>""", file = tlLogic)     
                        else:
                            continue
                    elif nint == number - 1 and tl.attrib.get('id') == '%s' % tlLogic_name[nint]:
                            with open(f"./IKSAN/add/its{idx}.xml", "a") as tlLogic:
                                try:
                                    print(f"""    <{tl.tag} id="{tl.attrib.get('id')}" type="{tl.attrib.get('type')}" programID="{", ".join(str(s) for s in phase_list[nint][phases])}" offset="{tl.attrib.get('offset')}">""", file = tlLogic)
                                except IndexError:
                                    print("</additional>", file = tlLogic)
                                    continue
                                for n in range(len(tl)):                               
                                    if n % 2 == 0:
                                        d = phase_list[nint][phases][int(n / 2)] - 4
                                    elif n % 2 != 0:
                                        d = 4
                                    print(f"""        <{tl[0].tag} duration="{d}" state="{tl[n].attrib.get('state')}"/>""", file = tlLogic)
                                print(f"""    </{tl.tag}>""", file = tlLogic)
                                print("</additional>", file = tlLogic)
            tl_list.append(tl.attrib.get('id')) 
                            
    def normal_tod_waitingtime(self, table, cen, k, number):
        
        with open(DIR_SUMO_CFG / f"clus.sumocfg", "w") as cfg :
            print("""<?xml version="1.0" encoding="UTF-8"?>""", file = cfg)
            print(f"""<configuration xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dir.de/xsd/sumoConfiguration.xsd">""", file = cfg)
            print("""    <input>""", file = cfg)
            print("""    <net-file value="../net/IKSAN.net.xml"/>
        <route-files value="../rou/clus.rou.xml"/>""", file = cfg)
            print("""    </input>""", file = cfg)
            print("""    <gui_only>
        <registry-viewport value="true"/>""", file = cfg)
            print("""    </gui_only>""", file = cfg)
            print("""</configuration>""" , file = cfg)
            
        traci.start(["sumo", "-c", DIR_SUMO_CFG / "clus.sumocfg",
                            "--tripinfo-output", "./IKSAN/out/tripinfoclus.xml"])

        step = 0

        while traci.simulation.getMinExpectedNumber() > 0:

            # for n in range(number):
            #     traci.trafficlight.setProgram(f"{tlLogic_name[n]}", )
            traci.trafficlight.setProgram("1.Sindong396-7", 0)
            traci.trafficlight.setProgram("2.sindong830", 0)
            traci.trafficlight.setProgram("3.sindong120-23", 0)
            traci.trafficlight.setProgram("4.yeongdengdong870", 0)
            traci.trafficlight.setProgram("5.yeongdengdong870-1", 0)
            traci.trafficlight.setProgram("6.eoyangdong663", 0)
            traci.trafficlight.setProgram("7.busongdong1060", 0)
            traci.trafficlight.setProgram("8.busongdongsan266-4", 0)
            traci.trafficlight.setProgram("9.busongdong224-8", 0)
            traci.trafficlight.setProgram("10.IKSANfirestation", 0)
            traci.simulationStep()
            step += 1

        traci.close()
        
        tree_tripinfo = ET.parse('./IKSAN/out/tripinfoclus.xml')
        root_tripinfo = tree_tripinfo.getroot()

        edge_from = []
        wait_time = []
        num_sum = []
        for n in range(len(table)):
            edge_from.append(table[n][0])
        
        for n in range(number):
            waiting_time = 0
            num = 0  
            for trip in root_tripinfo.iter('tripinfo'):
                if trip.get('id').split("_")[0] in edge_from:

                    waiting = trip.get('waitingTime')
                    waiting_time += float(waiting)
                    num += 1
                else: 
                    continue
            wait_time.append(waiting_time)
            num_sum.append(num)       
             
        return wait_time[number-1] / num_sum[number-1]        
        
    def cal_waiting_time(self, idx, table, cen, k, number):
        
        tree_tripinfo = ET.parse(f'./IKSAN/out/tripinfoits{idx}.xml')
        root_tripinfo = tree_tripinfo.getroot()
        
        edge_from = []
        wait_time = []
        num_sum = []
        
        for n in range(len(table)):
            edge_from.append(table[n][0])

        for n in range(number):
            waiting_time = 0
            num = 0
            for trip in root_tripinfo.iter('tripinfo'):
                if trip.get('id').split("_")[0] in edge_from:
                    
                    waiting = trip.get('waitingTime')
                    waiting_time += float(waiting)
                    num += 1
                else:
                    continue
            wait_time.append(waiting_time)
            num_sum.append(num)
            
        return wait_time[number - 1] / num_sum[number - 1]      
    
    def run_simulation(self, phase_list, idx, shm_name, nm, table, cen, k, number, tlLogic_name):
        waiting = []
        case = 1
        
        shl_ = shared_memory.ShareableList(name=shm_name)
        self.generate_cfgfile(idx)
        if number == 1:
            for phases in phase_list[0]:
            
                self.generate_addfile(idx, table, number, tlLogic_name, phases, phase_list)

                traci.start(["sumo", "-c", DIR_SUMO_CFG / f"its{idx}.sumocfg",
                                            "--tripinfo-output", f"./IKSAN/out/tripinfoits{idx}.xml", '--log', 'logfile2.txt'])

                step = 0
                before = time()
                while traci.simulation.getMinExpectedNumber() > 0:
                    
                    traci.simulationStep()
                    step += 1
                    
                traci.close()
                after = time()
                x = after - before

                waiting_time = self.cal_waiting_time(idx, table, cen, k, number)
                if len(phases) == 3:
                    print(f"PROC# {idx} CASE# {idx}-{case} : {phases[0],phases[1],phases[2]} avg_wait_time : {waiting_time} time: {x}")
                elif len(phases) == 4:    
                    print(f"PROC# {idx} CASE# {idx}-{case} : {phases[0],phases[1],phases[2],phases[3]} avg_wait_time : {waiting_time} time: {x}")
                elif len(phases) == 5:
                    print(f"PROC# {idx} CASE# {idx}-{case} : {phases[0],phases[1],phases[2],phases[3], phases[4]} avg_wait_time : {waiting_time} time: {x}")
                case += 1
                waiting.append(waiting_time)
                
            Improvement = float(1-(min(waiting))/float(nm))*100
            
            arg_ = np.argmin(waiting)
            
            if idx == 1:
                shl_[0] = phase_list[0][arg_][0]
                shl_[1] = phase_list[0][arg_][1]
                shl_[2] = phase_list[0][arg_][2]
                shl_[3] = phase_list[0][arg_][3]
                shl_[4] = Improvement
                
            if idx == 2:
                shl_[5] = phase_list[0][arg_][0]
                shl_[6] = phase_list[0][arg_][1]
                shl_[7] = phase_list[0][arg_][2]
                shl_[8] = phase_list[0][arg_][3]
                shl_[9] = Improvement
                
            if idx == 3:
                shl_[10] = phase_list[0][arg_][0]
                shl_[11] = phase_list[0][arg_][1]
                shl_[12] = phase_list[0][arg_][2]
                shl_[13] = phase_list[0][arg_][3]
                shl_[14] = Improvement
                
            if idx == 4:
                shl_[15] = phase_list[0][arg_][0]
                shl_[16] = phase_list[0][arg_][1]
                shl_[17] = phase_list[0][arg_][2]
                shl_[18] = phase_list[0][arg_][3]
                shl_[19] = Improvement
                
            if idx == 5:
                shl_[20] = phase_list[0][arg_][0]
                shl_[21] = phase_list[0][arg_][1]
                shl_[22] = phase_list[0][arg_][2]
                shl_[23] = phase_list[0][arg_][3]
                shl_[24] = Improvement
                
            if idx == 6:
                shl_[25] = phase_list[0][arg_][0]
                shl_[26] = phase_list[0][arg_][1]
                shl_[27] = phase_list[0][arg_][2]
                shl_[28] = phase_list[0][arg_][3]
                shl_[29] = Improvement
                
            if idx == 7:
                shl_[30] = phase_list[0][arg_][0]
                shl_[31] = phase_list[0][arg_][1]
                shl_[32] = phase_list[0][arg_][2]
                shl_[33] = phase_list[0][arg_][3]
                shl_[34] = Improvement
                
            if idx == 8:
                shl_[35] = phase_list[0][arg_][0]
                shl_[36] = phase_list[0][arg_][1]
                shl_[37] = phase_list[0][arg_][2]
                shl_[38] = phase_list[0][arg_][3]
                shl_[39] = Improvement    
                
        elif number > 1:
            phase_len = []
            # print(phase_list)
            for n in range(number):
                phase_len.append(len(phase_list[n]))
            # for phases in range(len(phase_list[phase_len.index(max(phase_len))])):
            for phases in range(max(phase_len)):
              
                    
                self.generate_addfile(idx, table, number, tlLogic_name, phases, phase_list)
                
                traci.start(["sumo", "-c", DIR_SUMO_CFG / f"its{idx}.sumocfg",
                                            "--tripinfo-output", f"./IKSAN/out/tripinfoits{idx}.xml", '--log', 'logfile.txt'])

                step = 0
                before = time()
                while traci.simulation.getMinExpectedNumber() > 0:
                
                    traci.simulationStep()
                    step += 1
                    
                traci.close()
                after = time()
                x = after - before

                waiting_time = self.cal_waiting_time(idx, table, cen, k, number)
                # DB 조정 후
                
                print(f"PROC# {idx} CASE# {idx}-{case}")
                for n in range(number):
                    try:
                        if len(phase_list[n][phases]) == 3:
                            print(f"NAME# {tlLogic_name[n]} : {phase_list[n][phases][0], phase_list[n][phases][1], phase_list[n][phases][2]} avg_wait_time : {waiting_time} time: {x}")
                            
                        elif len(phase_list[n][phases]) == 4:    
                            print(f"NAME# {tlLogic_name[n]} : {phase_list[n][phases][0], phase_list[n][phases][1], phase_list[n][phases][2], phase_list[n][phases][3]} avg_wait_time : {waiting_time} time: {x}")
                        
                        elif len(phase_list[n][phases]) == 5:
                            print(f"NAME# {tlLogic_name[n]} : {phase_list[n][phases][0], phase_list[n][phases][1], phase_list[n][phases][2], phase_list[n][phases][3], phase_list[n][phases][4]} avg_wait_time : {waiting_time} time: {x}")
                    except IndexError:
                        print(f"NAME# {tlLogic_name[n]} : Phase End")
                case += 1
                waiting.append(waiting_time)
