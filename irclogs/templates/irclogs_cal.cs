   <tr class="head">
    <th colspan="7"><?cs var:cal.year ?> <?cs var:cal.month ?></th>
   </tr>
   <tr class="days">
    <th>Mo</th>
    <th>Tu</th>
    <th>We</th>
    <th>Th</th>
    <th>Fr</th>
    <th>Sa</th>
    <th>So</th>
   </tr>
   <?cs each:week = cal.weeks ?>
    <tr class="week">
     <?cs each:day = week ?>
      <?cs if day.empty ?>
       <td class="empty">&nbsp;</td>
      <?cs else ?>
       <td class="<?cs if day.has_log ?>has_log<?cs 
        /if ?><?cs if:day.today ?> today<?cs
        /if ?>"><?cs if:day.has_log ?><a href="<?cs var:day.href ?>"><?cs var:day.caption ?></a><?cs else ?><?cs var:day.caption ?><?cs /if ?></td>
      <?cs /if ?>
     <?cs /each ?>
    </tr>
   <?cs /each ?>
   <tr class="nav">
    <td><a href="<?cs var:cal.prev_year.href ?>">◀</a></td>
    <td><a href="<?cs var:cal.prev_month.href ?>">◂</a></td>
    <td colspan="3">&nbsp;</td>
    <td><a href="<?cs var:cal.next_month.href ?>">▸</a></td>
    <td><a href="<?cs var:cal.next_year.href ?>">▶</a></td>
   </tr>
