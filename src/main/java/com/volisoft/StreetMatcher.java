package com.volisoft;

import com.wantedtech.common.xpresso.experimental.concurrency.MapReduce;
import com.wantedtech.common.xpresso.experimental.concurrency.Mapper;
import com.wantedtech.common.xpresso.experimental.concurrency.Reducer;
import com.wantedtech.common.xpresso.strings.FuzzyWuzzy;
import com.wantedtech.common.xpresso.types.list;
import com.wantedtech.common.xpresso.types.tuples.tuple2;
import com.wantedtech.common.xpresso.x;

public class StreetMatcher {


   static final list<String> streets = x.list();
   static {
      list<list<String>> data = x.list(x.csv("streets.csv","r","utf-8"));
      for (list<String> row : data) {
         streets.append(row.get(0));
      }
   }

   static Mapper<String,tuple2<Integer, String>> mapper = new Mapper<String,tuple2<Integer, String>>() {
      public void map(String streetToGuess) {
//         list<tuple2<Integer, String>> scores = x.list();
         for (String street : streets) {
            Integer score = FuzzyWuzzy.token_set_ratio(streetToGuess, street, true);
            tuple2<Integer, String> scorePair = x.tuple2(score, street);
            yield(streetToGuess, scorePair);
         }
      }
   };

   static Reducer<tuple2<Integer, String>, String> reducer = new Reducer<tuple2<Integer, String>, String>() {
      public void reduce(tuple2<String,list<tuple2<Integer, String>>> input) {
         Integer maxScore = -1;
         String bestMatch = "<no match>";
         for (tuple2<Integer, String> score : input.value) {
            if(maxScore < score.value0) {
               maxScore = score.value0;
               bestMatch = score.value1;
            }
         }
         yield(input.key, bestMatch);
      }
   };

   public static void main(String[] args) {
      System.out.println(FuzzyWuzzy.token_set_ratio("вул. малиновського", "ул. маршала малиновского", true));
      System.out.println(FuzzyWuzzy.token_set_ratio("вул. малиновського", "ул. Романовского", true));

      list<String> streetsMixed = x.list() ;
      list<list<String>> streetsCsv = x.list(x.csv("streets_mixed.csv", "r", "utf-8"));
      for (list<String> row : streetsCsv) {
         streetsMixed.append(row.get(1));
      }

      x.timer.start();
      MapReduce<String,tuple2<Integer,String>,String> result = x.<String, tuple2<Integer, String>, String>MapReduce(
              streetsMixed).map(mapper).reduce(reducer);
      x.print(x.timer.stop());
      x.print(result);
   }
}
