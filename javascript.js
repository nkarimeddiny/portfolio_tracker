$(function(){

$("#errorMessage").hide();
$("#submitbuttondiv").hide();
$("#calculateTotal").hide();
$("#savebutton").hide();
$("#calculate").hide();

$(".deletebutton").click(function(){
   var stockToDelete = $(this).siblings(".listedStock").val();
   $("#deleteStock").val(stockToDelete);
   $(this).hide();
   $(this).siblings(".deletebuttonarea").append($("#submitbuttondiv"));
   $(this).parent("td").append($("#submitbuttondiv"));
   $("#submitbuttondiv").show();
});


//code for calculating current dollar values, and percent changes
$("#calculate").click(function(){
  $("#stockentry").show();
  $(".deletebutton").show();

   var oldListedStocks = [];
   var newListedStocks = [];
   var oldNumberValues = $(".oldListedStock").length;
   var currentNumberValues = $(".newListedStock").length;
 
   //next three code blocks are for checking if any changes have been made to the portfolio
   if (oldNumberValues != currentNumberValues) {
      $("#errorMessage").show();
      return;
   }   
   
   for (var i = 0; i < oldNumberValues; i++){
      var oldListedStock = $(".oldListedStock").eq(i).text();
      oldListedStocks.push(oldListedStock);
      var newListedStock = $(".newListedStock").eq(i).text();
      newListedStocks.push(newListedStock);
   } 

   for (var i = 0; i < oldNumberValues; i++){
     if (oldListedStocks[i] != newListedStocks[i]) {
       $("#errorMessage").show();
       return;
     }
   }
   //end code for checking if changes have been made to the portfolio

   var oldValues = [];
   for (var i = 0; i < oldNumberValues; i++){
      var oldValue = $(".oldprice").eq(i)[0].value;
      oldValues.push(Number(oldValue));
   } 

   var oldDollarValues = [];
   var numberValues = $(".oldvalue").length;
   for (var i = 0; i < numberValues; i++){
      var oldDollarValue = $(".oldvalue").eq(i)[0].value;
      oldDollarValues.push(Number(oldDollarValue));
   } 

   var newValues = [];
   for (var i = 0; i < currentNumberValues; i++){
      var newValue = $(".current_price").eq(i)[0].value;
      newValues.push(Number(newValue));
   }

   var decimalChanges = [];
   for (var i = 0; i < oldValues.length; i++){
      var decimalChange = (newValues[i] - oldValues[i]) / oldValues[i];
      decimalChanges.push(decimalChange);
   }  

   var newDollarValues = [];
   for (var i = 0; i < oldDollarValues.length; i++){
      newDollarValues[i] = Number(oldDollarValues[i]) + (oldDollarValues[i] * decimalChanges[i]);
   }

   for (var i = 0; i < newDollarValues.length; i++){
      $(".dollar_value").eq(i)[0].value = newDollarValues[i].toFixed(5);
   }

   for (var i = 0; i < decimalChanges.length; i++){
      $(".percent_change").eq(i)[0].value = (decimalChanges[i] * 100).toFixed(2);
      if (decimalChanges[i] >= 0) {
         $(".arrow").eq(i)[0].setAttribute("class","arrow green");
      }
      else {
         $(".arrow").eq(i)[0].setAttribute("class","arrow red");     
      }  
   }

   $("#calculateTotal").show();

}); //end code for calculating current dollar values, and percent changes


 //code for calculating total holdings
 $("#calculateTotal").click(function(){
     var numberValues = $(".indiv_stock").length;
     var totalDollarValue = 0;
   for (var i = 0; i < numberValues; i++){
       var newValue = $(".indiv_stock").eq(i)[0].value;
       totalDollarValue += Number(newValue);
   }
   $("#totalHoldings").val(totalDollarValue.toFixed(5));
   $("#savebutton").show();
 });

 
 //code for requesting a previous date's portfolio data
 $(".olddates").click(function(event){
   var selectedDate = $(this).data("yearmonthday");
   $("#oldDate").val(selectedDate);
   $("#myForm").submit();
 });


 $("#s_and_p").focus(function(){
   $(this).val("");
 });

 $("#s_and_p").keydown(function(){
   $("#calculate").show();
 });

 $(".indiv_stock").keydown(function(){
   $("#calculateTotal").show();
 });

});//end ready
